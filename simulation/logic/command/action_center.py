from logic.command.action import action
from logic.command.command import command
from logic.command.command_center import command_center
import numpy as np

class action_center(object):
    def __init__(self, command_c : command_center) -> None:
        super().__init__()

        # list of actions
        self.action_list : list = []

        # action being executed at the moment
        self.current_action : action = None

        # connection to command center
        self.command_center : command_center = command_c

    def update(self):
        for a in self.action_list:
            a.update()

        # check if current action is finished and remove it
        if(self.current_action.is_finished()):
            self.action_list.pop(0)    
            # add next in line if exists
            if(len(self.action_list) > 0):
                self.current_action = self.action_list[0]
            else:
                self.current_action = None

        if(not self.current_action is None):
            self.current_action.update()
            
            new_commands = self.current_action.get_commands()
            for c in new_commands:
                command_center.register_command(c)    
                

    def register_action(self, action : action):
        self.action_list.append(action)