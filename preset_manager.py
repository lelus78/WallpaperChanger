import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from config import (
    DefaultPreset,
    Monitors,
    Provider,
    ProvidersSequence,
    Query,
    PurityLevel,
    ScreenResolution,
    WallhavenSorting,
    WallhavenTopRange,
)


def _ensure_list(value: Optional[List[str]]) -> List[str]:
    if not value:
        return []
    return [str(item) for item in value if str(item).strip()]


@dataclass
class Preset:
    name: str
    title: str
    description: str
    providers: List[str]
    queries: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)
    colors: List[str] = field(default_factory=list)
    ratios: List[str] = field(default_factory=list)
    purity: Optional[str] = None
    screen_resolution: Optional[str] = None
    wallhaven: Dict[str, str] = field(default_factory=dict)
    pexels: Dict[str, str] = field(default_factory=dict)

    def build_query(self, override_query: Optional[str] = None) -> str:
        base = override_query
        if not base:
            if self.queries:
                base = random.choice(self.queries)
            elif Query:
                base = Query
            else:
                base = ""

        tokens: List[str] = []
        if base:
            tokens.append(base.strip())

        for token in self.exclude:
            token = token.strip()
            if token:
                tokens.append(f"-{token}")

        return " ".join(tokens).strip()

    def get_wallhaven_settings(self) -> Dict[str, str]:
        settings = dict(self.wallhaven)
        if self.purity:
            settings.setdefault("purity", self.purity)
        if self.colors:
            settings.setdefault("colors", ",".join(self.colors))
        if self.ratios:
            settings.setdefault("ratios", ",".join(self.ratios))
        if self.screen_resolution:
            settings.setdefault("atleast", self.screen_resolution)
        return settings

    def get_pexels_settings(self) -> Dict[str, str]:
        settings = dict(self.pexels)
        if self.colors:
            settings.setdefault("color", self.colors[0])
        return settings


class PresetManager:
    def __init__(self, presets_data: Optional[List[Dict]] = None):
        if presets_data is None:
            try:
                from config import Presets  # type: ignore

                presets_data = Presets
            except ImportError:
                presets_data = []

        self.presets: Dict[str, Preset] = {}
        self.default_name = DefaultPreset if "DefaultPreset" in globals() else None

        if not presets_data:
            self._load_default()
        else:
            self._load_presets(presets_data)

        if not self.default_name or self.default_name not in self.presets:
            self.default_name = next(iter(self.presets))

        self.monitor_overrides = Monitors if isinstance(Monitors, list) else []

    def _load_default(self) -> None:
        default = Preset(
            name="default",
            title="Default",
            description="Default configuration",
            providers=self._resolve_providers(None),
            queries=[Query] if Query else [],
            exclude=[],
            colors=[],
            ratios=[],
            purity=PurityLevel,
            screen_resolution=ScreenResolution,
            wallhaven={
                "sorting": WallhavenSorting,
                "top_range": WallhavenTopRange,
            },
        )
        self.presets[default.name] = default
        self.default_name = default.name

    def _load_presets(self, presets_data: List[Dict]) -> None:
        for raw in presets_data:
            name = str(raw.get("name") or "").strip()
            if not name:
                continue
            preset = Preset(
                name=name,
                title=str(raw.get("title") or name).strip(),
                description=str(raw.get("description") or "").strip(),
                providers=self._resolve_providers(raw.get("providers")),
                queries=_ensure_list(raw.get("queries")),
                exclude=_ensure_list(raw.get("exclude")),
                colors=[color.lower() for color in _ensure_list(raw.get("colors"))],
                ratios=_ensure_list(raw.get("ratios")),
                purity=str(raw.get("purity") or PurityLevel).strip() or PurityLevel,
                screen_resolution=str(
                    raw.get("screen_resolution") or ScreenResolution
                ).strip()
                or ScreenResolution,
                wallhaven={
                    key: str(value).strip()
                    for key, value in dict(raw.get("wallhaven", {})).items()
                    if str(value).strip()
                },
                pexels={
                    key: str(value).strip()
                    for key, value in dict(raw.get("pexels", {})).items()
                    if str(value).strip()
                },
            )
            self.presets[preset.name] = preset

    def _resolve_providers(self, providers: Optional[List[str]]) -> List[str]:
        resolved = []
        source = providers or ProvidersSequence or [Provider]
        for provider in source:
            name = str(provider).strip().lower()
            if name and name not in resolved:
                resolved.append(name)
        if not resolved:
            resolved = [Provider]
        return resolved

    def list_presets(self) -> List[Preset]:
        return list(self.presets.values())

    def get_preset(self, name: Optional[str]) -> Preset:
        if name and name in self.presets:
            return self.presets[name]
        return self.presets[self.default_name]

    def get_monitor_override(self, index: int) -> Dict:
        if not self.monitor_overrides:
            return {}
        idx = min(index, len(self.monitor_overrides) - 1)
        override = self.monitor_overrides[idx]
        if isinstance(override, dict):
            return override
        return {}

    def pick_query(self, preset: Preset, override_query: Optional[str] = None) -> str:
        return preset.build_query(override_query)
