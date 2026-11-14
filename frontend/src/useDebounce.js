import { useEffect, useState } from "react";

/*
  Wait until the user stops typing before using the value.

  Without this the list pages send a request on every keystroke, and the
  answers can come back in the wrong order. The timer restarts on each
  change, so only the last value survives.
*/
function useDebounce(value, delay = 400) {
  const [settled, setSettled] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return settled;
}

export default useDebounce;
