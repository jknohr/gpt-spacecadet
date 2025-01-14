from utils.utils import step_already_finished
from helpers.Agent import Agent
import json
from utils.style import color_green_bold
from const.function_calls import ARCHITECTURE
import platform

from utils.utils import should_execute_step, generate_app_data
from database.database import save_progress, get_progress_steps
from logger.logger import logger
from helpers.AgentConvo import AgentConvo

ARCHITECTURE_STEP = 'architecture'


class Architect(Agent):
    def __init__(self, project):
        super().__init__('architect', project)
        self.convo_architecture = None

    def get_architecture(self):
        print(json.dumps({
            "project_stage": "architecture"
        }), type='info')

        self.project.current_step = ARCHITECTURE_STEP

        # If this app_id already did this step, just get all data from DB and don't ask user again
        step = get_progress_steps(self.project.args['app_id'], ARCHITECTURE_STEP)
        if step and not should_execute_step(self.project.args['step'], ARCHITECTURE_STEP):
            step_already_finished(self.project.args, step)
            self.project.architecture = None
            self.project.system_dependencies = None
            self.project.package_dependencies = None
            db_data = step["architecture"]
            if db_data:
                if isinstance(db_data, dict):
                    self.project.architecture = db_data["architecture"]
                    self.project.system_dependencies = db_data["system_dependencies"]
                    self.project.package_dependencies = db_data["package_dependencies"]
                elif isinstance(db_data, list):
                    self.project.architecture = ""
                    self.project.system_dependencies = [
                        {
                            "name": dep,
                            "description": "",
                            "test": "",
                            "required_locally": False
                        } for dep in db_data
                    ]
                    self.project.package_dependencies = []
            return

        print(color_green_bold("Planning project architecture...\n"))
        logger.info("Planning project architecture...")

        self.convo_architecture = AgentConvo(self)
        llm_response = self.convo_architecture.send_message('architecture/technologies.prompt',
            {'name': self.project.args['name'],
             'app_summary': self.project.project_description,
             'clarifications': self.project.clarifications,
             'user_stories': self.project.user_stories,
             'user_tasks': self.project.user_tasks,
             "os": platform.system(),
             'app_type': self.project.args['app_type']}, ARCHITECTURE)

        self.project.architecture = llm_response["architecture"]
        self.project.system_dependencies = llm_response["system_dependencies"]
        self.project.package_dependencies = llm_response["package_dependencies"]

        # TODO: Project.args should be a defined class so that all of the possible args are more obvious
        if self.project.args.get('advanced', False):
            llm_response = self.convo_architecture.get_additional_info_from_user(ARCHITECTURE)
            if llm_response is not None:
                self.project.architecture = llm_response["architecture"]
                self.project.system_dependencies = llm_response["system_dependencies"]
                self.project.package_dependencies = llm_response["package_dependencies"]

        logger.info(f"Final architecture: {self.project.architecture}")

        save_progress(self.project.args['app_id'], self.project.current_step, {
            "messages": self.convo_architecture.messages,
            "architecture": llm_response,
            "app_data": generate_app_data(self.project.args)
        })

        return
