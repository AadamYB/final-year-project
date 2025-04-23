import React, { useState, useEffect, useRef } from "react";
import styles from "./DebugConsole.module.css";

const DebugConsole = () => {
    const [input, setInput] = useState("");
    const [history, setHistory] = useState([]);
    const inputRef = useRef();
    const bottomRef = useRef();

    useEffect(() => {
        inputRef.current?.focus();
    }, []);

    // So that the terminal follows the input field when there is an overflow - user doesn't need to scroll = GREAT
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [history, input]);

    // This is how the commands are executed - to be mapped to backend
    const handleKeyDown = (e) => {
    if (e.key === "Enter") {
        const prompt = "user@ip-address:~$ ";
        let outputLine = prompt + input;
        switch (input.trim()) {
        case "ls":
            outputLine += "\nlist whatever";
            break;
        case "pwd":
            outputLine += "\nyou are doing something";
            break;
        default:
            outputLine += "\nUnknown Cmd";
        }

        setHistory((prev) => [...prev, outputLine]);
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

        <hr/>

        <div
            className={styles.terminal}
            onClick={() => inputRef.current?.focus()}
        >
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