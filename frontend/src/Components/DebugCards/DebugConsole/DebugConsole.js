import React, { useState, useEffect, useRef } from "react";
import styles from "./DebugConsole.module.css";
import io from "socket.io-client";
const socket = io("http://13.40.55.105:5000"); // (already existing socket)

const DebugConsole = ({repoTitle}) => {
  const [input, setInput] = useState("");
  const [history, setHistory] = useState([]);
  const inputRef = useRef();
  const bottomRef = useRef();

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history]);

  useEffect(() => {
    socket.on("console-output", (data) => {
      setHistory((prev) => [...prev, data.output]);
    });

    return () => {
      socket.off("console-output");
    };
  }, []);

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      const prompt = "user@ip-address:~$ ";
      const fullInput = prompt + input;
      setHistory((prev) => [...prev, fullInput]);

      socket.emit("console-command", { command: input, repoTitle });  
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
            <span className={styles.prompt}>user@ip-address:~$ </span>
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