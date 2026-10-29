import { useCallback, useEffect, useState } from 'react';

export const PLAYBACK_SECONDS = 20;

// O relógio controla somente a apresentação do histórico já calculado.
export function usePlayback(history) {
  const [position, setPosition] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const last = Math.max(0, history.length - 1);
  const selected = Math.min(last, Math.floor(position + 1e-8));
  const finished = selected >= last;

  useEffect(() => {
    if (!playing || finished || last === 0) return undefined;
    let previous = performance.now();
    const timer = window.setInterval(() => {
      const now = performance.now();
      const elapsed = now - previous;
      previous = now;
      setPosition((value) => Math.min(last, value + elapsed * speed * last / (PLAYBACK_SECONDS * 1000)));
    }, 40);
    return () => window.clearInterval(timer);
  }, [playing, speed, last, history, finished]);

  useEffect(() => {
    if (finished) setPlaying(false);
  }, [finished]);

  function seek(index) {
    setPlaying(false);
    setPosition(Math.max(0, Math.min(last, index)));
  }

  function restart(autoplay = true) {
    setPosition(0);
    setPlaying(autoplay);
  }

  function toggle() {
    if (finished) setPosition(0);
    setPlaying((value) => !value);
  }

  const pause = useCallback(() => setPlaying(false), []);

  return { selected, playing: playing && !finished, speed, setSpeed, finished,
    seconds: last ? position / last * PLAYBACK_SECONDS : 0,
    duration: last ? PLAYBACK_SECONDS : 0, seek, restart, toggle,
    pause };
}
