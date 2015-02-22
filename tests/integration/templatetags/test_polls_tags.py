# -*- coding: utf-8 -*-

# Standard library imports
# Third party imports
from django.db.models import get_model
from django.template import Context
from django.template.base import Template
from django.test import TestCase
from django.test.client import RequestFactory
from guardian.shortcuts import assign_perm

# Local application / specific library imports
from machina.core.loading import get_class
from machina.test.factories import create_category_forum
from machina.test.factories import create_forum
from machina.test.factories import create_topic
from machina.test.factories import GroupFactory
from machina.test.factories import PostFactory
from machina.test.factories import TopicPollFactory
from machina.test.factories import TopicPollOptionFactory
from machina.test.factories import TopicPollVoteFactory
from machina.test.factories import UserFactory

Forum = get_model('forum', 'Forum')
Post = get_model('forum_conversation', 'Post')
Topic = get_model('forum_conversation', 'Topic')

PermissionHandler = get_class('forum_permission.handler', 'PermissionHandler')


class BasePollsTagsTestCase(TestCase):
    def setUp(self):
        self.loadstatement = '{% load url from future %}{% load forum_polls_tags %}'
        self.request_factory = RequestFactory()

        self.g1 = GroupFactory.create()
        self.u1 = UserFactory.create()
        self.u2 = UserFactory.create()
        self.u1.groups.add(self.g1)
        self.u2.groups.add(self.g1)
        self.moderators = GroupFactory.create()
        self.moderator = UserFactory.create()
        self.moderator.groups.add(self.moderators)
        self.superuser = UserFactory.create(is_superuser=True)

        # Permission handler
        self.perm_handler = PermissionHandler()

        # Set up a top-level category
        self.top_level_cat = create_category_forum()

        # Set up some forums
        self.forum_1 = create_forum(parent=self.top_level_cat)
        self.forum_2 = create_forum(parent=self.top_level_cat)

        # Set up some topics and posts
        self.forum_1_topic = create_topic(forum=self.forum_1, poster=self.u1)
        self.forum_2_topic = create_topic(forum=self.forum_2, poster=self.u2)
        self.post_1 = PostFactory.create(topic=self.forum_1_topic, poster=self.u1)
        self.post_2 = PostFactory.create(topic=self.forum_2_topic, poster=self.u2)
        self.poll_1 = TopicPollFactory.create(topic=self.forum_1_topic)
        self.poll_2 = TopicPollFactory.create(topic=self.forum_2_topic)

        # Assign some permissions
        assign_perm('can_see_forum', self.g1, self.forum_1)
        assign_perm('can_read_forum', self.g1, self.forum_1)
        assign_perm('can_edit_own_posts', self.g1, self.forum_1)
        assign_perm('can_delete_own_posts', self.g1, self.forum_1)
        assign_perm('can_reply_to_topics', self.g1, self.forum_1)
        assign_perm('can_see_forum', self.moderators, self.forum_1)
        assign_perm('can_read_forum', self.moderators, self.forum_1)
        assign_perm('can_edit_own_posts', self.moderators, self.forum_1)
        assign_perm('can_delete_own_posts', self.moderators, self.forum_1)
        assign_perm('can_edit_posts', self.moderators, self.forum_1)
        assign_perm('can_delete_posts', self.moderators, self.forum_1)
        assign_perm('can_vote_in_polls', self.g1, self.forum_1)


class TestCanBeCompletedByTag(BasePollsTagsTestCase):
    def test_can_tell_if_a_user_can_vote_in_a_poll(self):
        # Setup
        def get_rendered(poll, user):
            request = self.request_factory.get('/')
            request.user = user
            t = Template(self.loadstatement + '{% if poll|can_be_completed_by:request.user %}CAN_VOTE{% else %}CANNOT_VOTE{% endif %}')
            c = Context({'poll': poll, 'request': request})
            rendered = t.render(c)

            return rendered

        # Run & check
        self.assertEqual(get_rendered(self.poll_1, self.u1), 'CAN_VOTE')
        self.assertEqual(get_rendered(self.poll_2, self.u1), 'CANNOT_VOTE')
        self.assertEqual(get_rendered(self.poll_1, self.superuser), 'CAN_VOTE')
        self.assertEqual(get_rendered(self.poll_2, self.superuser), 'CAN_VOTE')


class TestHasBeenCompletedByTag(BasePollsTagsTestCase):
    def test_can_if_a_user_has_already_voted_in_a_poll(self):
        # Setup
        def get_rendered(poll, user):
            request = self.request_factory.get('/')
            request.user = user
            t = Template(self.loadstatement + '{% if poll|has_been_completed_by:request.user %}HAS_VOTED{% else %}HAS_NOT_VOTED{% endif %}')
            c = Context({'poll': poll, 'request': request})
            rendered = t.render(c)

            return rendered

        # Setup
        poll_option_1 = TopicPollOptionFactory.create(poll=self.poll_1)
        TopicPollOptionFactory.create(poll=self.poll_1)
        TopicPollVoteFactory.create(poll_option=poll_option_1, voter=self.u1)

        # Run & check
        self.assertEqual(get_rendered(self.poll_1, self.u1), 'HAS_VOTED')
        self.assertEqual(get_rendered(self.poll_2, self.u1), 'HAS_NOT_VOTED')
