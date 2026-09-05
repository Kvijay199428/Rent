import { useEffect, useState } from "react";

export default function useCapsLock(): boolean {
  const [isOn, setIsOn] = useState(false);

  useEffect(() => {
    const update = (e: KeyboardEvent) => {
      setIsOn(e.getModifierState && e.getModifierState("CapsLock"));
    };

    const onKeyDown = (e: KeyboardEvent) => update(e);
    const onKeyUp = (e: KeyboardEvent) => update(e);
    const onFocusIn = (e: FocusEvent) => {
      const t = e.target;
      if (t instanceof HTMLInputElement) {
        const el = t as HTMLInputElement & {
          getModifierState?: (key: string) => boolean;
        };
        setIsOn(
          typeof el.getModifierState === "function" &&
            !!el.getModifierState("CapsLock")
        );
      }
    };

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    window.addEventListener("focusin", onFocusIn);

    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
      window.removeEventListener("focusin", onFocusIn);
    };
  }, []);

  return isOn;
}