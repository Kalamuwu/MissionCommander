#!/usr/bin/env python3

from .gui import ControllerGUI
from .cli import ControllerCLI
# from missioncommander import launch_client, launch_server

if __name__ == '__main__':
    import argparse

    def __configure_client_parser(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("-a", "--address",   required=True,              type=str, help="the address of the server to connect to")
        parser.add_argument("-p", "--port",      required=True,              type=int, help="the server port to connect to")
       #parser.add_argument("-t", "--timeout",   required=False, default=8,  type=int, help="number of seconds to attempt client reconnect until giving up; negative values mean attempt indefinitely")
    
    def __configure_server_parser(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("-i", "--interface", required=False, default='', type=str, help="the interface to bind the server to; '' (empty string) bind the server to all available interfaces")
        parser.add_argument("-p", "--port",      required=True,              type=int, help="the port to bind the server to")
       #parser.add_argument("-t", "--timeout",   required=False, default=8,  type=int, help="number of seconds to attempt client reconnect until giving up; negative values mean attempt indefinitely")
    
    def __configure_gui_parser(parser: argparse.ArgumentParser) -> None:
        pass
    
    def __configure_cli_parser(parser: argparse.ArgumentParser) -> None:
        pass
    
    # general config
    parser = argparse.ArgumentParser(prog='missioncommander', description=f'Launches a GUI or CLI client/server controller.')
    subparsers = parser.add_subparsers(dest='interface_type', required=True, help='The type of controller to launch')
    
    # # client-specific options
    # parser_client = subparsers.add_parser('client')
    # __configure_client_parser(parser_client)
    
    # # server-specific options
    # parser_server = subparsers.add_parser('server')
    # __configure_server_parser(parser_server)
    
    # gui-specific options
    parser_gui = subparsers.add_parser('gui')
    __configure_gui_parser(parser_gui)
    
    # cli-specific options
    parser_cli = subparsers.add_parser('cli')
    __configure_cli_parser(parser_cli)
    
    # implement and use dual parser
    args = vars(parser.parse_args())
    con_type = args.pop('interface_type').lower()
    controller = ControllerGUI() if con_type == 'gui' else ControllerCLI()
    controller.setup(args)
    controller.launch()
