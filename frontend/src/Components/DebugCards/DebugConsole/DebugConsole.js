import React, { useEffect, useRef } from "react";
import { Terminal } from "xterm";
import "xterm/css/xterm.css";
import io from "socket.io-client";
import styles from "./DebugConsole.module.css";

const socket = io("http://13.40.55.105:5000");

const DebugConsole = ({ repoTitle }) => {
  const terminalRef = useRef();

  useEffect(() => {
    if (!repoTitle) return;
  
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
  
    term.open(terminalRef.current);
    term.focus();
    term.write('\r\n');
  
    // Input handler
    term.onData(data => {
      socket.emit("console-command", {
        command: data,
        repoTitle,
      });
    });
  
    // Output handler to show our cmd stdout in the terminal
    socket.on("console-output", (data) => {
      term.write(data.output);
    });
  
    // Only able to debug after repoTitle exists
    socket.emit("start-debug", { repo: repoTitle });
  
    return () => {
      socket.emit("stop-debug", { repo: repoTitle });
      socket.off("console-output");
      term.dispose();
    };
  }, [repoTitle]);

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