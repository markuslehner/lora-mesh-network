from logic.command.command import command

class action(object):
    def __init__(self) -> None:
        super().__init__()

        self.finished = False

        self.commands_to_be_sent = []

    def update(self):
        pass

    def get_commands(self) -> list:
        copy = self.commands_to_be_sent.copy()
        self.commands_to_be_sent = []
        return copy

    def is_finished(self) -> bool:
        return self.finished