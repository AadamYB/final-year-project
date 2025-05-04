import React, { useState, useEffect, useRef } from "react";
import styles from "./DebugConsole.module.css";
import io from "socket.io-client";

const socket = io("http://13.40.55.105:5000");

const DebugConsole = ({ buildId, repoTitle, isPaused }) => {
  const [input, setInput] = useState("");
  const [history, setHistory] = useState([]);
  const [prompt, setPrompt] = useState("user@13.40.55.105:~$ ");
  const inputRef = useRef();
  const bottomRef = useRef();
  const hasStartedRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history]);

  useEffect(() => {
    if (!repoTitle || !isPaused || !buildId) return;
    if (hasStartedRef.current === buildId) return;

    hasStartedRef.current = buildId;
    socket.emit("start-debug", { repo: repoTitle, build_id: buildId });
  }, [repoTitle, buildId, isPaused]);

  useEffect(() => {
    socket.on("console-output", (data) => {
      setHistory((prev) => [...prev, data.output]);
    });

    socket.on("prompt-update", (data) => {
      if (data.prompt) {
        setPrompt(data.prompt);
      }
    });

    return () => {
      // Only stop debug session if it was started and pipeline is still paused
      if (hasStartedRef.current === buildId && isPaused) {
        socket.emit("stop-debug", { build_id: buildId });
      }

      socket.off("console-output");
      socket.off("prompt-update");
      hasStartedRef.current = null;
    };
  }, [buildId, isPaused]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      const fullInput = prompt + input;
      setHistory((prev) => [...prev, fullInput]);

      socket.emit("console-command", {
        command: input,
        repoTitle,
        buildId: buildId,
      });

      setInput("");
    }
  };

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
      <div className={styles.terminal} onClick={() => inputRef.current?.focus()}>
        <div className={styles.console}>
          {history.map((line, i) => (
            <pre key={i} className={styles.consoleLine}>
              {line}
            </pre>
          ))}
          <div className={styles.inputLine}>
            <span className={styles.prompt}>{prompt}</span>
            <span className={styles.displayedWrapper}>
              <span className={styles.displayedInput}>{input}</span>
              <span className={styles.cursor}></span>
            </span>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              className={styles.hiddenInput}
              autoComplete="off"
            />
            <div ref={bottomRef} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default DebugConsole;