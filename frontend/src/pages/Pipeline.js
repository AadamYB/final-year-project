import React, { useState } from "react";
import styles from "../styles/Pipeline.module.css";
import YamlEditorCard from "../Components/PipelineCards/YamlEditor/YamlEditor";
import UploadSelectCard from "../Components/PipelineCards/UploadSelectCard/UploadSelectCard";
import PipelineVisualiser from "../Components/PipelineCards/PiplineVisualiser/PipelineVisualiser";

const PipelinePage = () => {
  const [yamlText, setYamlText] = useState("");

  return (
    <div className={styles.page}>
        <div className={styles.headerSection}>
            <h1>Pipeline Configuration</h1>
        </div>

      <div className={styles.topSection}>
        <YamlEditorCard yamlText={yamlText} onChange={e => setYamlText(e.target.value)} />
        <UploadSelectCard />
      </div>

      
      <PipelineVisualiser />
    </div>
  );
};

export default PipelinePage;