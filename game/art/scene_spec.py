from __future__ import annotations

from dataclasses import asdict, dataclass

from pydantic import BaseModel, ConfigDict, Field


SCENE_TYPE_PRESETS: dict[str, dict[str, str]] = {
    "mountain_guardian_scene": {
        "scene_type": "mountain_guardian_scene",
        "subject": "guardian sentinel",
        "subject_pose": "frontal guarding stance",
        "secondary_object": "ritual blade",
        "environment": "gaia mountain sanctuary",
        "symbol": "chakana",
        "energy": "sacred wind",
        "palette": "gold violet turquoise",
        "camera": "hero medium close",
        "mood": "solemn vigilant",
    },
    "hyperborea_temple_scene": {
        "scene_type": "hyperborea_temple_scene",
        "subject": "hyperborean champion",
        "subject_pose": "heroic raised weapon",
        "secondary_object": "solar axe",
        "environment": "polar citadel observatory",
        "symbol": "solar chakana",
        "energy": "solar light",
        "palette": "ice blue silver white",
        "camera": "hero medium close",
        "mood": "ancient luminous",
    },
    "archon_void_scene": {
        "scene_type": "archon_void_scene",
        "subject": "archon hierophant",
        "subject_pose": "seated throne decree",
        "secondary_object": "seal tablet",
        "environment": "void throne realm",
        "symbol": "corrupt seal",
        "energy": "void sparks",
        "palette": "black crimson toxic green",
        "camera": "ominous low angle",
        "mood": "oppressive malign",
    },
    "ritual_duel_scene": {
        "scene_type": "ritual_duel_scene",
        "subject": "ritual duelist",
        "subject_pose": "combat advance",
        "secondary_object": "ceremonial spear",
        "environment": "astral plateau",
        "symbol": "chakana duel sigil",
        "energy": "aura glow",
        "palette": "gold violet turquoise",
        "camera": "dynamic side close",
        "mood": "tense heroic",
    },
    "sacred_beast_scene": {
        "scene_type": "sacred_beast_scene",
        "subject": "sacred beast",
        "subject_pose": "profile leap",
        "secondary_object": "relic collar",
        "environment": "sacred forest",
        "symbol": "ancestral rune",
        "energy": "cosmic wind",
        "palette": "gold violet turquoise",
        "camera": "wide low angle",
        "mood": "mythic wild",
    },
}


class SceneSpecModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    scene_type: str
    subject: str
    subject_pose: str
    secondary_object: str
    environment: str
    symbol: str
    energy: str
    palette: str
    camera: str
    mood: str
    subject_kind: str = ""
    object_kind: str = ""
    environment_kind: str = ""
    subject_ref: str = ""
    object_ref: str = ""
    environment_ref: str = ""


class ArtSceneRuntimeModel(BaseModel):
    model_config = ConfigDict(extra='allow', str_strip_whitespace=True)

    scene_type: str = Field(default='mountain_guardian_scene')
    subject: str = Field(default='guardian sentinel')
    subject_pose: str = Field(default='frontal guarding stance')
    secondary_object: str = Field(default='ritual blade')
    environment: str = Field(default='gaia mountain sanctuary')
    symbol: str = Field(default='chakana')
    energy: str = Field(default='sacred wind')
    palette: str = Field(default='gold violet turquoise')
    camera: str = Field(default='hero medium close')
    mood: str = Field(default='solemn vigilant')
    subject_kind: str = ""
    object_kind: str = ""
    environment_kind: str = ""
    subject_ref: str = ""
    object_ref: str = ""
    environment_ref: str = ""


@dataclass(slots=True)
class SceneSpec:
    scene_type: str
    subject: str
    subject_pose: str
    secondary_object: str
    environment: str
    symbol: str
    energy: str
    palette: str
    camera: str
    mood: str
    subject_kind: str = ""
    object_kind: str = ""
    environment_kind: str = ""
    subject_ref: str = ""
    object_ref: str = ""
    environment_ref: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    def to_model(self) -> SceneSpecModel:
        return SceneSpecModel(**self.to_dict())


def validate_scene_semantic(payload: dict[str, object]) -> dict[str, object]:
    model = ArtSceneRuntimeModel(**payload)
    return model.model_dump()


def default_scene_type(environment_kind: str, subject_kind: str) -> str:
    env = str(environment_kind or "").lower()
    subj = str(subject_kind or "").lower()
    if "citadel" in env or "hyperborean" in subj:
        return "hyperborea_temple_scene"
    if "throne" in env or "archon" in subj:
        return "archon_void_scene"
    if "beast" in subj or "animal" in subj:
        return "sacred_beast_scene"
    if "weapon" in subj:
        return "ritual_duel_scene"
    return "mountain_guardian_scene"


def build_scene_spec(
    *,
    scene_type: str,
    subject: str,
    subject_pose: str,
    secondary_object: str,
    environment: str,
    symbol: str,
    energy: str,
    palette: str,
    camera: str,
    mood: str,
    subject_kind: str = "",
    object_kind: str = "",
    environment_kind: str = "",
    subject_ref: str = "",
    object_ref: str = "",
    environment_ref: str = "",
) -> SceneSpec:
    model = SceneSpecModel(
        scene_type=scene_type,
        subject=subject,
        subject_pose=subject_pose,
        secondary_object=secondary_object,
        environment=environment,
        symbol=symbol,
        energy=energy,
        palette=palette,
        camera=camera,
        mood=mood,
        subject_kind=subject_kind,
        object_kind=object_kind,
        environment_kind=environment_kind,
        subject_ref=subject_ref,
        object_ref=object_ref,
        environment_ref=environment_ref,
    )
    return SceneSpec(**model.model_dump())


def scene_spec_prompt_fragment(spec: SceneSpec) -> str:
    return (
        f"scene type {spec.scene_type}, "
        f"subject pose {spec.subject_pose}, "
        f"secondary object {spec.secondary_object}, "
        f"camera {spec.camera}, "
        f"mood {spec.mood}, "
        f"symbol {spec.symbol}, "
        f"energy {spec.energy}"
    )
