import { act, cleanup, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { usePlayback } from './usePlayback';

beforeEach(() => vi.useFakeTimers());
afterEach(() => { cleanup(); vi.useRealTimers(); });
const history = Array.from({ length: 101 }, (_, iteration) => ({ iteration }));
function advance(ms) { act(() => vi.advanceTimersByTime(ms)); }

describe('reprodução do histórico', () => {
  it('avança por 20 segundos, pausa e continua do mesmo ponto', () => {
    const { result } = renderHook(() => usePlayback(history));
    act(() => result.current.restart());
    advance(4000);
    expect(result.current.selected).toBeCloseTo(20, 0);
    act(() => result.current.toggle());
    const paused = result.current.selected;
    advance(3000);
    expect(result.current.selected).toBe(paused);
    act(() => result.current.toggle());
    advance(17000);
    expect(result.current.selected).toBe(100);
    expect(result.current.playing).toBe(false);
  });

  it('muda a velocidade, navega manualmente e reinicia ao rever', () => {
    const { result } = renderHook(() => usePlayback(history));
    act(() => { result.current.restart(); result.current.setSpeed(2); });
    advance(5000);
    expect(result.current.selected).toBeCloseTo(50, 0);
    act(() => result.current.seek(80));
    advance(1000);
    expect(result.current.selected).toBe(80);
    expect(result.current.playing).toBe(false);
    act(() => result.current.seek(100));
    act(() => result.current.toggle());
    expect(result.current.selected).toBe(0);
    expect(result.current.playing).toBe(true);
  });

  it('encerra timers ao desmontar e trata histórico com apenas um passo', () => {
    const { result, unmount } = renderHook(() => usePlayback(history));
    act(() => result.current.restart());
    expect(vi.getTimerCount()).toBe(1);
    unmount();
    expect(vi.getTimerCount()).toBe(0);
    const single = [{ iteration: 0 }];
    const one = renderHook(() => usePlayback(single));
    act(() => one.result.current.restart(false));
    expect(one.result.current.finished).toBe(true);
    expect(one.result.current.duration).toBe(0);
    expect(vi.getTimerCount()).toBe(0);
  });
});
