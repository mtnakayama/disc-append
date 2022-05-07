#!/usr/bin/env python

from __future__ import annotations

import argparse
from collections.abc import Collection
import dataclasses
from dataclasses import dataclass
from enum import auto, Enum
from pathlib import Path
import subprocess
from typing import Optional, Union
import re

import humanfriendly


class Command(Enum):
    INIT = auto()
    APPEND = auto()

    @classmethod
    def list_command_options(cls) -> list[str]:
        return [x.name.lower() for x in cls]

    @classmethod
    def from_command_option(cls, value: str) -> Command:
        return cls[value.upper()]


@dataclass
class RunConfig:
    command: Command
    device: Path
    source_paths: Collection[Path]
    speed: int
    dry_run: bool = False
    volume_id: Optional[str] = None


def main():
    run_config = parse_arguments()

    match run_config.command:
        case Command.INIT:
            if run_config.volume_id is None:
                raise RuntimeError("You must specify a Volume ID when initializing a disc.")
        case Command.APPEND:
            if run_config.volume_id is None:
                volume_id = get_volume_id(run_config.device)
                print('Using volume id:', volume_id)
                run_config.volume_id = volume_id

    confirmation = confirmation_prompt(run_config)

    if confirmation and not run_config.dry_run:
        disc_write(run_config)
        media_info = read_media_info(run_config.device)
        print_bytes_free(media_info)


def confirmation_prompt(run_config: RunConfig) -> bool:
    disc_write(dataclasses.replace(run_config, dry_run=True))

    print('')
    print_size_approximations(run_config)

    print_disc_write_error_messages(run_config)

    print('')
    while True:
        key = input("Would you like to proceed? [y/N]:").lower()
        if key == 'y':
            return True
        elif key == 'n' or key == '':
            return False


def print_size_approximations(run_config: RunConfig):
    media_info = read_media_info(run_config.device)

    print_bytes_free(media_info)
    approx_write_size = get_bytes_to_be_written(run_config)
    print(
        'Approx. '
        f'{humanfriendly.format_size(approx_write_size, binary=True)} '
        'to be written.'
    )

    size_left = media_info.free_size - approx_write_size
    print(
        'Approx.',
        f'{humanfriendly.format_size(size_left, binary=True)}',
        'will be free after the operation.'
    )


def print_bytes_free(media_info: MediaInfo):
    print(
        f'{humanfriendly.format_size(media_info.free_size, binary=True)}',
        'bytes free on disc.'
    )


def parse_arguments() -> RunConfig:
    parser = argparse.ArgumentParser(description='Modify a multi-session disc.')
    parser.add_argument('command', type=str,
                        choices=Command.list_command_options())
    parser.add_argument('device', type=Path,
                        help='path to destination disc')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--volume-id', '-V',
                        help=('specifies the volume ID (volume name or label) '
                              'to be written into the master block'))
    parser.add_argument('--speed', type=int, default=1,
                        help='the speed to burn the disc')
    parser.add_argument('source_paths', type=Path, nargs='+',
                        help='paths to add to the disc')
    args = parser.parse_args()

    run_config = RunConfig(
        command=Command.from_command_option(args.command),
        device=args.device,
        source_paths=args.source_paths,
        dry_run=args.dry_run,
        volume_id=args.volume_id,
        speed=args.speed
    )

    return run_config


MKISOFS_BASE_ARGS = ['-iso-level', '3', '-l', '-T', '-R', '-J', '--joliet-long']
SESSION_FLAGS = {Command.INIT: '-Z', Command.APPEND: '-M'}


def disc_write(run_config: RunConfig):
    disc_write_impl(run_config)


def print_disc_write_error_messages(run_config: RunConfig):
    completed_process = disc_write_impl(
        dataclasses.replace(run_config, dry_run=True),
        capture_output=True,
        print_executing=False
    )
    if 'already carries isofs' in completed_process.stderr:
        print('')
        print(
            '\033[31;1;4m',
            "WARNING: THIS DISC ALREADY HAS AN EXISTING FILESYSTEM.\n",
            "If you continue, your existing data will be lost.\n",
            "(Use the `append` command if you wish to append data instead.)",
            '\033[0m'
        )


def disc_write_impl(run_config: RunConfig, capture_output=False,
                    print_executing=True):
    if run_config.volume_id is None:
        raise ValueError("volume_id cannot be none.")

    session_flag = SESSION_FLAGS[run_config.command]

    dry_run_flag = ['--dry-run'] if run_config.dry_run else []

    args = (
        ['growisofs']
        + dry_run_flag
        + [f'--speed={run_config.speed}']
        + [session_flag, str(run_config.device)]
        + MKISOFS_BASE_ARGS
        + ['-V', run_config.volume_id]
        + [str(x) for x in run_config.source_paths]
    )
    if print_executing:
        print('Executing:', args)

    return subprocess.run(args, capture_output=capture_output, check=True,
                          text=True)


def get_bytes_to_be_written(run_config: RunConfig) -> int:
    args = (
        ['mkisofs']
        + MKISOFS_BASE_ARGS
        + ['--print-size', '--quiet']
        + [str(x) for x in run_config.source_paths]
    )
    completed_process = subprocess.run(
        args,
        capture_output=True, check=True, text=True
    )

    sectors_to_be_written = int(completed_process.stdout)
    bytes_to_be_written = sectors_to_be_written * 2048

    return bytes_to_be_written


def get_volume_id(device: Path) -> str:
    args = ['blkid', '--output', 'value', '--match-tag', 'LABEL', '/dev/sr0']

    completed_process = subprocess.run(
        args,
        capture_output=True, check=True, text=True
    )

    volume_id = completed_process.stdout.strip()

    return volume_id


@dataclass
class MediaInfo:
    total_size: int  # in bytes
    free_size: int  # in bytes
    used_size: int  # in bytes
    is_blank: bool


def read_media_info(device: Path) -> MediaInfo:
    args = [
        'dvd+rw-mediainfo', str(device)
    ]
    completed_process = subprocess.run(
        args,
        capture_output=True, check=True, text=True
    )

    return parse_media_info(completed_process.stdout)


TOTAL_SPACE_REGEX = re.compile(r'(\d+)\*')


def parse_media_info(info: str) -> MediaInfo:
    media_info_tree = build_media_info_tree(info)
    try:
        total_size_str, *_ = media_info_tree['READ FORMAT CAPACITIES']['00h(3000)'].split('*')  # type: ignore
        total_size = int(total_size_str) * 2048
    except KeyError:
        total_size_str, *_ = media_info_tree['READ CAPACITY'].split('*')  # type: ignore
        total_size = int(total_size_str) * 2048

    is_blank = media_info_tree['READ DISC INFORMATION']['Disc status'] == 'blank'

    if is_blank:
        free_size = total_size
    else:
        for _, child in media_info_tree.items():
            try:
                free_size_str, *_ = child['Free Blocks'].split('*')
                free_size = int(free_size_str) * 2048
            except KeyError:
                pass
            except TypeError:
                pass

    used_size = total_size - free_size

    return MediaInfo(total_size=total_size, free_size=free_size,
                     used_size=used_size, is_blank=is_blank)


MediaInfoTree = dict[str, Union[str, dict[str, str]]]


def build_media_info_tree(info: str) -> MediaInfoTree:
    media_info_tree: MediaInfoTree = {}

    current_child: Optional[dict[str, str]] = None
    for line in info.split('\n'):
        if not line.strip() or line[0] == ':':
            pass
        elif line[0] == ' ':
            child_child_key, child_child_value = line.split(':')
            current_child[child_child_key.strip()] = child_child_value.strip()  # type: ignore  # noqa
        else:
            child_key, child_value_str = line.split(':')
            child_key = child_key.strip()
            child_value: Union[str, dict[str, str]] = child_value_str.strip()

            if child_value:
                current_child = None
            else:
                child_value = {}
                current_child = child_value

            media_info_tree[child_key] = child_value

    return media_info_tree



if __name__ == '__main__':
    main()
