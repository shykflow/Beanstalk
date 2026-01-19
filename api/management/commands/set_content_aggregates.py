import argparse
from django.core.management.base import BaseCommand
import logging

from api.models import (
    Comment,
    Experience,
    Playlist,
    Post,
)
import api.utils.commands as commands

logger = logging.getLogger('app')

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--process-all',
            default=False,
            action=argparse.BooleanOptionalAction,
            help='Run all sub functions without asking')

    def handle(self, *args, **options):
        should_process_all: bool = options['process_all']
        should_process_experiences = False
        should_process_playlists = False
        should_process_posts = False
        should_process_comments = False
        if should_process_all:
            should_process_experiences = True
            should_process_playlists = True
            should_process_posts = True
            should_process_comments = True
        else:
            should_process_experiences = input('Process experiences [y/N]: ') \
                .strip().lower() == 'y'
            should_process_playlists = input('Process playlists [y/N]: ') \
                .strip().lower() == 'y'
            should_process_posts = input('Process posts [y/N]: ') \
                .strip().lower() == 'y'
            should_process_comments = input('Process comments [y/N]: ') \
                .strip().lower() == 'y'
        if should_process_experiences:
            self.process_experiences()
            print()
        if should_process_playlists:
            self.process_playlists()
            print()
        if should_process_posts:
            self.process_posts()
            print()
        if should_process_comments:
            self.process_comments()
            print()

    def process_experiences(self):
        handled_ids = []
        total_count = Experience.objects.all().count()
        print(f'Total experiences: {total_count}')
        while len(handled_ids) < total_count:
            qs = Experience.objects.exclude(id__in=handled_ids)[:100]
            items: list[Experience] = list(qs)
            for item in items:
                item.calc_and_save_all_aggregates()
            handled_ids += [x.id for x in items]
            commands.print_progress(
                on=len(handled_ids),
                outof=total_count,
                decimal_places=2)

    def process_playlists(self):
        handled_ids = []
        total_count = Playlist.objects.all().count()
        print(f'Total playlists: {total_count}')
        while len(handled_ids) < total_count:
            qs = Playlist.objects.exclude(id__in=handled_ids)[:100]
            items: list[Playlist] = list(qs)
            for item in items:
                item.calc_and_save_all_aggregates()
            handled_ids += [x.id for x in items]
            commands.print_progress(
                on=len(handled_ids),
                outof=total_count,
                decimal_places=2)

    def process_posts(self):
        handled_ids = []
        total_count = Post.objects.all().count()
        print(f'Total posts: {total_count}')
        while len(handled_ids) < total_count:
            qs = Post.objects.exclude(id__in=handled_ids)[:100]
            items: list[Post] = list(qs)
            for item in items:
                item.calc_and_save_all_aggregates()
            handled_ids += [x.id for x in items]
            commands.print_progress(
                on=len(handled_ids),
                outof=total_count,
                decimal_places=2)

    def process_comments(self):
        handled_ids = []
        total_count = Comment.objects.all().count()
        print(f'Total comments: {total_count}')
        while len(handled_ids) < total_count:
            qs = Comment.objects.exclude(id__in=handled_ids)[:100]
            items: list[Comment] = list(qs)
            for item in items:
                item.calc_and_save_all_aggregates()
            handled_ids += [x.id for x in items]
            commands.print_progress(
                on=len(handled_ids),
                outof=total_count,
                decimal_places=2)
