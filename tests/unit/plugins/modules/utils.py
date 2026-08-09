# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


class ModuleResult(Exception):
    def __init__(self, values):
        super().__init__(values)
        self.values = values


class ModuleExit(ModuleResult):
    pass


class ModuleFail(ModuleResult):
    pass


class FakeModule:
    def __init__(self, params, check_mode=False):
        self.check_mode = check_mode
        self.params = params

    def exit_json(self, **values):
        raise ModuleExit(values)

    def fail_json(self, **values):
        raise ModuleFail(values)
