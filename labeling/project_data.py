from enums import AnnotationMode, AnnotationStage


from dataclasses import dataclass


@dataclass
class ProjectData:
    id: int
    uid: str
    stage: AnnotationStage
    mode: AnnotationMode

    def to_json(self):
        data_dict = {
            'id': self.id,
            'uid': self.uid,
            'stage': self.stage.name,
            'mode': self.mode.name
        }
        return data_dict