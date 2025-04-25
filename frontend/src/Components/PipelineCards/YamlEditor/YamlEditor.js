import { useRef } from "react";
import { Editor } from "@monaco-editor/react";
import styles from "./YamlEditor.module.css";

const YamlEditorCard = ({ yamlText, setYamlText }) => {
  const editorRef = useRef(null);

  const handleSave = () => {
    const blob = new Blob([yamlText], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = ".ci.yaml";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleReset = () => {
    setYamlText("");
  };

  return (
    <div className={styles.card}>
        <h3>Edit YAML file Configuration</h3>

        <div className={styles.editorWrapper}>
            <Editor
                height="100%"
                width="100%"
                language="yaml"
                value={yamlText} // ✅ use `value`, not `defaultValue`
                theme="vs-dark"
                onMount={(editor) => {
                    editorRef.current = editor;
                    editor.focus();
                }}
                onChange={(val) => setYamlText(val || "")}
                options={{
                    fontSize: 14,
                    fontFamily: "Fira Code, monospace",
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    tabSize: 2,
                    renderIndentGuides: true,
                    lineNumbers: "on",
                    wordWrap: "on",
                    stickyScroll: {
                    enabled: false,
                    },
                }}
            />
        </div>

      <div className={styles.buttonRow}>
        <button className={styles.save} onClick={handleSave}>Save</button>
        <button className={styles.reset} onClick={handleReset}>Reset</button>
      </div>
    </div>
  );
};

export default YamlEditorCard;