import React, { useState } from "react";
import styles from "../styles/Pipeline.module.css";
import YamlEditorCard from "../Components/PipelineCards/YamlEditor/YamlEditor";
import UploadSelectCard from "../Components/PipelineCards/UploadSelectCard/UploadSelectCard";
import PipelineVisualiser from "../Components/PipelineCards/PiplineVisualiser/PipelineVisualiser";
import { CODE_SNIPPETS } from "../constants/yamlTemplates"; // Optional: Template source

const PipelinePage = () => {
  const [yamlText, setYamlText] = useState("");

  // Handle file upload
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

  // Handle template selection
  const handleTemplateChange = (snippet) => {
    setYamlText(snippet);
  };

  return (
    <div className={styles.page}>
      <div className={styles.headerSection}>
        <h1>Pipeline Configuration</h1>
      </div>

      <div className={styles.topSection}>
        <YamlEditorCard yamlText={yamlText} setYamlText={setYamlText} />
        <UploadSelectCard onUpload={handleUpload} onTemplateChange={handleTemplateChange} />
      </div>

      <PipelineVisualiser />
    </div>
  );
};

export default PipelinePage;