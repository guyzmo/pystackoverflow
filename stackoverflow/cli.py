#!/usr/bin/env python

import os
import sys
import pprint
import getpass
import argparse

from stackoverflow.stackexchange import StackExchange
from stackoverflow.auth_google import StackOverflow_GoogleAuth
from stackoverflow.auth_stackoverflow import StackOverflow_SOAuth
from stackoverflow.utils import DictConfig, html2md, authenticate

def prt(s):
    print s


def run():
    # http://stackoverflow.com/questions/3609852/which-is-the-best-way-to-allow-configuration-options-be-overridden-at-the-comman
    conf_parser = argparse.ArgumentParser(prog=sys.argv[0],
                                          description='Stackoverflow CLI',
        # Don't mess with format of description
        # formatter_class=argparse.RawDescriptionHelpFormatter,
        # Turn off help, so we print all options in response to -h
                                          add_help=False
    )
    conf_parser.add_argument('-c', '--config',
                             dest='config',
                             default='~/.so.config',
                             help='Specify config file', metavar='FILE')
    conf_parser.add_argument('-C', '--cache',
                             dest='cache',
                             default='~/.so.cache.json',
                             help='Specify cache file', metavar='FILE')
    conf_parser.add_argument('-l', '--list',
                             dest='list',
                             action='store_true',
                             help='List all stackoverflow sites')
    args, remaining_argv = conf_parser.parse_known_args()

    if args.config and os.path.exists(args.config):
        config = DictConfig(args.config).as_dict()
    else:
        config = {
            'auth':{
                'provider': 'stackoverflow',
                'username': '',
                'password': ''},
            'default':{
                'cookiejar': None
            }
        }

    if args.list:
        for site in StackExchange(args.cache).list_sites():
            print "{} {}\n{}{}".format(("<"+site['site_url']+">").rjust(38),
                                       site['name'].ljust(35),
                                       " "*39,
                                       site['audience'])
        sys.exit(0)

    parser = argparse.ArgumentParser(prog=sys.argv[0],
                                     description='Stackoverflow CLI',
                                     parents=[conf_parser])
    parser.set_defaults(**config['default'])

    parser.add_argument('-j', '--jar',
                             dest='cookiejar',
                             default = "~/.so.cookie.jar",
                             help='Specify where to store the cookies', metavar='FILE')

    parser.add_argument('SITE',
                        action='store',
                        help='Canonical name of the targetted SO site')

    subparsers = parser.add_subparsers(
                        help='Stackoverflow commands',
                        dest='commands')

    pp = pprint.PrettyPrinter(indent=4)

    inbox_sp = subparsers.add_parser('inbox',
                          help = 'Notification inbox')
    chat_sp = subparsers.add_parser('chat',
                          help = 'Chat commands')
    qna_sp = subparsers.add_parser('qna',
                          help = 'Q&A commands')

    # NOTIFICATION INBOX

    @authenticate
    def inbox_list(so, args):
        pp.pprint(so.get_inbox())

    @authenticate
    def inbox_new(so, args):
        pp.pprint([n for n in so.get_inbox() if n['IsNew'] is True])

    @authenticate
    def inbox_mark(so, args):
        raise NotImplementedError

    inbox_ssp = inbox_sp.add_subparsers(dest='inbox',
                                        help='Commands for the notification inbox')

    inbox_ssp.add_parser('list',
                         help='List notifications').set_defaults(func=inbox_list)
    inbox_ssp.add_parser('new',
                         help='List new notifications').set_defaults(func=inbox_new)
    inbox_ssp.add_parser('mark',
                         help='Mark notification as read').set_defaults(func=inbox_mark)

    # CHAT

    @authenticate
    def chat_list(so, args):
        pp.pprint(so.list_all_rooms())

    @authenticate
    def chat_room_users(so, args):
        for u in so.get_room_users(args.ROOM):
            pp.pprint(u)

    @authenticate
    def chat_room_info(so, args):
        pp.pprint(so.get_room_info(args.ROOM))

    @authenticate
    def chat_read(so, args):
        print "Watching room #%d" % (args.ROOM)
        cb = lambda e:prt("%s: %s" % (e['user_name'].rjust(15),
                                      html2md(e['content'], 140)[:-2]))
        refresh = so.connect_to_chat(args.ROOM, cb=cb)
        while True:
            refresh()

    @authenticate
    def chat_write(so, args):
        so.send_to_chat(args.ROOM, args.MESSAGE)

    chat_ssp = chat_sp.add_subparsers(dest='chat',
                                       help='Commands for the SO chat system')
    chat_ssp.add_parser('list',
                 help='List all rooms').set_defaults(func=chat_list)

    p = chat_ssp.add_parser('info',
                 help='Get room info')
    p.set_defaults(func=chat_room_info)
    p.add_argument('ROOM',
                   action='store',
                   type=int,
                   help='Id of the room to get info')

    p = chat_ssp.add_parser('users',
                 help='Get room user list')
    p.set_defaults(func=chat_room_users)
    p.add_argument('ROOM',
                   action='store',
                   type=int,
                   help='Id of the room to get the list of users')

    p = chat_ssp.add_parser('watch',
                 help='Watch a room')
    p.set_defaults(func=chat_read)
    p.add_argument('ROOM',
                   action='store',
                   type=int,
                   help='Id of the room to watch')

    p = chat_ssp.add_parser('send',
                        help='Send a message to a room')
    p.set_defaults(func=chat_write)
    p.add_argument('ROOM',
                   action='store',
                   type=int,
                   help='Id of the room to send a message to')
    p.add_argument('MESSAGE',
                   action='store',
                   help='message to send to the room')

    # Q&A

    def qna_questions(so, args):
        pp.pprint([q for q in so.get_questions(args.sort, args.number)])

    def qna_answers(so, args):
        pp.pprint(so.get_answers(args.QUESTION))

    def qna_search(so, args):
        pp.pprint(so.lookup_question(args.QUERY))

    qna_ssp = qna_sp.add_subparsers(dest='qna',
                                    help='Commands for the SO Q&A system')
    p = qna_ssp.add_parser('questions',
                           help='List all questions')
    p.set_defaults(func=qna_questions)
    p.add_argument('-s', '--sort',
                   choices=['newest',
                            'featured',
                            'frequent',
                            'votes',
                            'active',
                            'unanswered'],
                   action='store',
                   dest='sort')
    p.add_argument('-n', '--number',
                   action='store',
                   dest='number')

    qna_ssp.add_parser('search',
                       help='Search a question').set_defaults(func=qna_search)
    p = qna_ssp.add_parser('answers',
                       help='Get answers for a question')
    p.set_defaults(func=qna_answers)
    p.add_argument('QUESTION',
                   action='store',
                   help='Question to get answers\' list')

    args = parser.parse_args(sys.argv[1:])

    if 'provider' in config['auth'].keys():
        if config['auth']['provider'] == 'stackoverflow':
            StackOverflow = StackOverflow_SOAuth
        elif config['auth']['provider'] == 'google':
            StackOverflow = StackOverflow_GoogleAuth
        else:
            print "Error: wrong openid provider given: %s" % config['auth']['provider']
            sys.exit(1)

    with StackOverflow(config['auth']['username'],
                       config['auth']['password'],
                       args.SITE,
                       args.cookiejar) as so:
        args.func(so, args)


if __name__ == "__main__":
    run()

