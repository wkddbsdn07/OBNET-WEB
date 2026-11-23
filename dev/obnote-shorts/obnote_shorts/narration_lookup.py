"""Read-only narration cache inventory for upstream-style storyboards."""
from .voice_cache import VoiceCache
from .voice_key import voice_key


def inspect_narration(storyboard: dict, cache: VoiceCache, *, language: str, voice: str,
                      provider: str, model_revision: str, sample_rate_hz: int,
                      channels: int, speed_percent: int) -> dict:
    """Return 1-based hits (scene -> path) and missing scenes in playback order.

    all_cached means files exist, not that speech, duration, or rights are verified.
    No writes, synthesis callbacks, network clients, fallback, or job transitions.
    """
    segments = storyboard.get('segments') if isinstance(storyboard, dict) else None
    if not isinstance(segments, list) or not segments:
        raise ValueError('Expected a nonempty storyboard segment list')
    hits = {}
    missing = []
    for scene, segment in enumerate(segments, 1):
        if not isinstance(segment, dict) or 'narration' not in segment:
            raise ValueError(f'Missing narration in scene {scene}')
        key = voice_key(text=segment['narration'], language=language, voice=voice,
                        provider=provider, model_revision=model_revision, sample_rate_hz=sample_rate_hz,
                        channels=channels, speed_percent=speed_percent)
        path = cache.lookup(key)
        if path is None:
            missing.append(scene)
        else:
            hits[scene] = path
    return {'status': 'pending' if missing else 'all_cached', 'hits': hits, 'missing': missing}
