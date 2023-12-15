import shlex
import logging

from typing import Dict, Any, List, Tuple, Union

from missioncommander.client import Client
from missioncommander.server import Server

# make logger for this module
import logging
logging.getLogger('missioncommander.gui')


class CommandReturn:
    """ Contains return status information for the given command. """
    
    RAN_OK = 0
    """ Command ran OK. """

    WARNING = 1
    """ Command returned with a warning. """

    RAN_OK_WITH_WARNING = RAN_OK | WARNING
    """ Command ran OK, but returned a warning. """
    
    BAD_CMD = 2
    """ Invalid command. """

    BAD_STATE = BAD_CMD | 4
    """ Cannot use this command in the current program state. """

    VAR_ISSUE = 8
    """ There was some issue(s) with the given variable(s). """

    IGNORED_VAR = RAN_OK_WITH_WARNING | VAR_ISSUE
    """ More variables were given than required. """

    BAD_VAR_TYPE = BAD_CMD | VAR_ISSUE
    """ Variable was not of correct type (e.x. string passed for integer value). """
    
    MISSING_INFO = 16
    """ Information was missing from the command. """
    
    MISSING_VAR = MISSING_INFO | VAR_ISSUE
    """ A required or optional variable was missing. """

    USED_DEFAULT_PARAM = RAN_OK_WITH_WARNING | MISSING_VAR
    """ Command ran OK; used default values for missing variables. """

    MISSING_REQUIRED_VAR = BAD_CMD | MISSING_VAR
    """ A required variable was not found. """

    # helper func
    @classmethod
    def _ok_check_length(cls, length: int, cmd: List[str]):
        return cls.RAN_OK if len(cmd) == length else cls.IGNORED_VAR


class ControllerCLI:
    def __init__(self):
        self.server = Server()
        self.client = Client()
        self.__should_run = False
    

    def setup(self, args: Dict[str, Any]) -> None:
        self.__should_run = True
    

    def __parse(self, cmd: List[str]) -> Tuple[Union[CommandReturn, None], str]:
        if len(cmd) == 0:
            return (None, "Nothing to parse")
        cmd[0] = cmd[0].lower()
        
        if cmd[0] in ['quit', 'exit']:
            self.__should_run = False
            return (CommandReturn._ok_check_length(1, cmd), "Exiting")
        
        if cmd[0] == 'help':
            return (CommandReturn._ok_check_length(1, cmd), "Command syntax:  {client/server} <verb> [args...]")

        # make sure interface is OK
        if cmd[0] not in ['client', 'server']:
            return (CommandReturn.BAD_CMD, f"Unknown controller '{cmd[0]}'")
        is_client = (cmd[0] == 'client')  # helper
        
        # make sure there's a verb
        if len(cmd) == 1:
            return (CommandReturn.MISSING_REQUIRED_VAR, f"{cmd[0]}: No verb specified")
        verb = cmd[1].lower()
        
        if verb == 'set':
            # make sure there's a field
            if len(cmd) == 2:
                return (CommandReturn.MISSING_REQUIRED_VAR, f"{cmd[0]}: set: No field specified")
            field = cmd[2].lower()
            # make sure field is valid
            if not ((is_client and field in ['address', 'port', 'client_id']) or (not is_client and field in ['interface', 'port'])):
                return (CommandReturn.BAD_VAR_TYPE, f"{cmd[0]}: set: Unknown field {field}")
            # make sure there's a value
            if len(cmd) == 3:
                return (CommandReturn.MISSING_REQUIRED_VAR, f"{cmd[0]}: set {field}: No value specified")
            state = cmd[3].lower()
            # is field port?
            if field == 'port':
                # check type
                try:
                    state = int(state)
                except ValueError:
                    return (CommandReturn.BAD_VAR_TYPE, f"{cmd[0]}: set port: {state} is not a valid integer")
                else:
                    if is_client:  self.client.port = state
                    else:          self.server.port = state
                    return (CommandReturn._ok_check_length(4, cmd), f"Set {cmd[0]} field port to {state}")
            # is field client.address?
            if field == 'address':
                self.client.address = state
                return (CommandReturn._ok_check_length(4, cmd), f"Set client field address to {state}")
            # is field client.client_id?
            if field == 'client_id':
                self.client.client_id = state
                return (CommandReturn._ok_check_length(4, cmd), f"Set client field client_id to {state}")
            # is field server.interface?
            if field == 'interface':
                self.server.interface = state
                return (CommandReturn._ok_check_length(4, cmd), f"Set server field interface to {state}")
        
        if verb == 'get':
            # make sure there's a field
            if len(cmd) == 2:
                return (CommandReturn.MISSING_REQUIRED_VAR, f"{cmd[0]}: get: No field specified")
            field = cmd[2].lower()
            # make sure field is valid
            if not ((field == 'port') or (is_client and field == 'address') or (not is_client and field == 'interface')):
                return (CommandReturn.BAD_VAR_TYPE, f"{cmd[0]}: get: Unknown field {field}")
            # is field port?
            if field == 'port':
                if is_client:  return (CommandReturn._ok_check_length(3, cmd), str(self.client.port))
                else:          return (CommandReturn._ok_check_length(3, cmd), str(self.server.port))
            # is field client.address?
            if field == 'address':
                return (CommandReturn._ok_check_length(3, cmd), str(self.client.address))
            # is field server.interface?
            if field == 'interface':
                return (CommandReturn._ok_check_length(3, cmd), str(self.server.interface))
        
        if verb == 'start':
            if is_client: self.client.start()
            else:         self.server.start()
            return (CommandReturn._ok_check_length(2, cmd), f"{cmd[0]}: Started")
                
        if verb == 'stop':
            if is_client:  self.client.stop()
            else:          self.server.stop()
            return (CommandReturn._ok_check_length(2, cmd), f"{cmd[0]}: Stopped")
        
        if verb == 'status':
            if is_client:  return (CommandReturn._ok_check_length(2, cmd), str(self.client.status))
            else:          return (CommandReturn._ok_check_length(2, cmd), str(self.server.status))
        
        if is_client and verb == 'connect':
            self.client.connect()
            return (CommandReturn._ok_check_length(2, cmd), "client: Connected")
        
        if is_client and verb == 'disconnect':
            self.client.disconnect()
            return (CommandReturn._ok_check_length(2, cmd), "client: Disconnected")
        
        if not is_client and verb == 'send':
            self.server.send(cmd[2])
            return (CommandReturn._ok_check_length(3, cmd), f"server: Sent message {shlex.quote(cmd[2])}")
        
        if verb == 'help':
            if is_client:  return (CommandReturn._ok_check_length(2, cmd), "client: Known verbs: set, get, connect, disconnect, start, stop, status")
            else:          return (CommandReturn._ok_check_length(2, cmd), "server: Known verbs: set, get, start, stop, status, send")
        
        if verb == 'status':
            if is_client:  return(CommandReturn._ok_check_length(2, cmd), str(self.client.status))
            else:          return(CommandReturn._ok_check_length(2, cmd), str(self.server.status))
        
        return (CommandReturn.BAD_CMD, f"{cmd[0]}: Unknown verb {verb}")


    def launch(self) -> None:
        while self.__should_run:
            try:
                cmd = input('> ')
            except KeyboardInterrupt:
                self.__should_run = False
                continue

            try:
                retcode, retval = self.__parse(shlex.split(cmd))
                print(retval)
            except Exception as e:
                logging.exception(e)
