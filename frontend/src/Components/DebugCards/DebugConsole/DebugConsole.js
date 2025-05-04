import React, { useEffect, useRef } from "react";
import { Terminal } from "xterm";
import "xterm/css/xterm.css";
import io from "socket.io-client";
import styles from "./DebugConsole.module.css";

const socket = io("http://13.40.55.105:5000");

const DebugConsole = ({ buildId, repoTitle, isPaused }) => {
  const terminalRef = useRef();
  const hasStartedRef = useRef(null); // Use null instead of false for clarity

  useEffect(() => {
    if (!repoTitle || !isPaused || !buildId) return;

    if (hasStartedRef.current === buildId) return;
    hasStartedRef.current = buildId;

    socket.emit("start-debug", { repo: repoTitle, build_id: buildId });

    const term = new Terminal({
      fontFamily: "monospace",
      fontSize: 14,
      theme: {
        background: "#1e1e1e",
        foreground: "#d4d4d4",
      },
      cursorBlink: true,
      scrollback: 500,
    });

    requestAnimationFrame(() => {
      if (terminalRef.current?.offsetWidth > 0) {
        term.open(terminalRef.current);
        term.focus();
        term.write("\r\n");
      }
    });

    term.onData((data) => {
      socket.emit("console-command", {
        command: data,
        repoTitle,
        build_id: buildId,
      });
    });

    socket.on("console-output", (data) => {
      term.write(data.output);
    });

    return () => {
      socket.emit("stop-debug", { build_id: buildId });
      socket.off("console-output");
      term.dispose();
    };
  }, [repoTitle, buildId, isPaused]);

  return (
    <div className={styles.container}>
      <div className={styles.debugTitle}>
        <img
          src={`${process.env.PUBLIC_URL}/icons/bug.png`}
          alt="BUG"
          className={styles.bugIcon}
        />
        <h3> Debug Console </h3>
      </div>
      <hr />
      <div className={styles.terminalWrapper}>
        <div ref={terminalRef} className={styles.terminalContainer} />
      </div>
    </div>
  );
};

export default DebugConsole;