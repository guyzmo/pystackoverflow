#!/usr/bin/env python

import os
import sys
import pprint
import getpass
import argparse

from stackoverflow.stackexchange import StackExchange
from stackoverflow.auth_google import StackOverflow_GoogleAuth
from stackoverflow.auth_stackoverflow import StackOverflow_SOAuth
from stackoverflow.utils import DictConfig

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
    conf_parser.add_argument('-l', '--list',
                             dest='list',
                             action='store_true',
                             help='List all stackoverflow sites')
    args, remaining_argv = conf_parser.parse_known_args()

    if args.list:
        for site in StackExchange().list():
            print "%s %s\n%s%s" % (("<"+site['url']+">").rjust(38),
                                   site['name'].ljust(35),
                                   " "*39,
                                   site['desc'])
        sys.exit(0)

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

    parser = argparse.ArgumentParser(prog=sys.argv[0],
                                     description='Stackoverflow CLI',
                                     parents=[conf_parser])
    parser.set_defaults(**config['default'])

    parser.add_argument('-j', '--jar',
                             dest='cookiejar',
                             default=None,
                             help='Specify where to store the cookies', metavar='FILE')

    parser.add_argument('SITE',
                        action='store',
                        default='stackoverflow.com',
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

    def inbox_list(so, args):
        pp.pprint(so.get_inbox())

    def inbox_new(so, args):
        pp.pprint([n for n in so.get_inbox() if n['IsNew'] is True])

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

    def chat_list(so, args):
        pp.pprint(so.list_all_rooms())

    def chat_read(so, args):
        print "Watching room #%d" % (args.ROOM)
        cb = lambda e:prt("%s: %s" % (e['user_name'].rjust(15), e['content']))
        so.connect_to_chat(args.ROOM, cb=cb)

    def chat_write(so, args):
        so.send_to_chat(args.ROOM, args.MESSAGE)

    chat_ssp = chat_sp.add_subparsers(dest='chat',
                                       help='Commands for the SO chat system')
    chat_ssp.add_parser('list',
                 help='List all rooms').set_defaults(func=chat_list)

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
        pp.pprint(so.get_questions().text)

    def qna_answers(so, args):
        pp.pprint(so.get_answers(args.QUESTION))

    def qna_search(so, args):
        pp.pprint(so.lookup_question(args.QUERY))

    qna_ssp = qna_sp.add_subparsers(dest='qna',
                                    help='Commands for the SO Q&A system')
    qna_ssp.add_parser('questions',
                       help='List all questions').set_defaults(func=qna_questions)
    qna_ssp.add_parser('search',
                       help='Search a question').set_defaults(func=qna_search)
    qna_ssp.add_parser('answers',
                       help='Get answers for a question').set_defaults(func=qna_answers)

    args = parser.parse_args(sys.argv[1:])

    if 'provider' in config['auth'].keys():
        if config['auth']['provider'] == 'stackoverflow':
            StackOverflow = StackOverflow_SOAuth
        elif config['auth']['provider'] == 'google':
            StackOverflow = StackOverflow_GoogleAuth
        else:
            print "Error: wrong openid provider given: %s" % config['auth']['provider']
            sys.exit(1)

    with StackOverflow_SOAuth(config['auth']['username'],
                              config['auth']['password'],
                              args.SITE,
                              args.cookiejar) as so:
        args.func(so, args)


def test():
    site = raw_input('Choose the stackoverflow site you want:')
    prov = raw_input('Choose your openid provider [1 for StackOverflow, 2 for Google]: ')
    name = raw_input('Enter your OpenID address: ')
    pswd = raw_input('Enter your password: ')
    if '1' in prov:
        so = StackOverflow_SOAuth(name, pswd, site)
    elif '2' in prov:
        so = StackOverflow_GoogleAuth(name, pswd, site)
    else:
        print "Error no openid provider given"

    pp = pprint.PrettyPrinter(indent=4)

    # GET INBOX
    # pp.pprint(so.get_inbox())

    # GET LIST OF ROOMS
    # pp.pprint(so.list_all_rooms())

    # SEND DATA TO A CHATROOM
    # so.send_to_chat(38, "\\\\_o< .o(quack!)")

    # CONNECT AND WATCH A CHATROOM
    cb = lambda e:prt("%s: %s" % (e['user_name'].rjust(15), e['content']))
    so.connect_to_chat(31366, cb=cb)


if __name__ == "__main__":
    run()

