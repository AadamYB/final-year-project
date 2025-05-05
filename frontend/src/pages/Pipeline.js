// PipelinePage.js
import React, { useState, useEffect } from "react";
import styles from "../styles/Pipeline.module.css";
import YamlEditorCard from "../Components/PipelineCards/YamlEditor/YamlEditor";
import UploadSelectCard from "../Components/PipelineCards/UploadSelectCard/UploadSelectCard";
import PipelineVisualiser from "../Components/PipelineCards/PiplineVisualiser/PipelineVisualiser";

const DEFAULT_REPO = "AadamYB_noughts-N-crosses"; // TODO: Dynamically set these based on PR or context
const BRANCH_NAME = "feature_MiniMaxAI"; // TODO ^


const PipelinePage = () => {
  const [yamlText, setYamlText] = useState("");

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await fetch(`http://35.177.242.182:5000/pipeline-config/${DEFAULT_REPO}?branch=${BRANCH_NAME}`);
        const data = await res.json();
        if (data?.content) setYamlText(data.content);
      } catch (err) {
        console.error("Failed to fetch .ci.yml:", err);
      }
    };
    fetchConfig();
  }, []);

  const handleUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target.result;
      setYamlText(text);
    };
    reader.readAsText(file);
  };

  const handleTemplateChange = (snippet) => {
    setYamlText(snippet);
  };

  // 💾 Server-side save function
  const saveConfig = async () => {
    try {
      const res = await fetch(`http://35.177.242.182:5000/pipeline-config/${DEFAULT_REPO}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: yamlText }),
      });
      const data = await res.json();
      if (data?.status === "success") {
        alert("✅ Saved .ci.yml to server!");
      } else {
        alert("❌ Save failed.");
      }
    } catch (err) {
      alert("❌ Failed to save config to server.");
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.headerSection}>
        <h1>Pipeline Configuration</h1>
      </div>

      <div className={styles.topSection}>
        <YamlEditorCard
          yamlText={yamlText}
          setYamlText={setYamlText}
          onSaveToServer={saveConfig} // ✅ Pass as prop
        />
        <UploadSelectCard onUpload={handleUpload} onTemplateChange={handleTemplateChange} />
      </div>

      <PipelineVisualiser />
    </div>
  );
};

export default PipelinePage;