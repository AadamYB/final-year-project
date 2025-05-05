import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import yaml from "js-yaml";
import styles from "../styles/Pipeline.module.css";
import YamlEditorCard from "../Components/PipelineCards/YamlEditor/YamlEditor";
import UploadSelectCard from "../Components/PipelineCards/UploadSelectCard/UploadSelectCard";
import PipelineVisualiser from "../Components/PipelineCards/PiplineVisualiser/PipelineVisualiser";

const PipelinePage = () => {
  const { buildId } = useParams();
  const [yamlText, setYamlText] = useState("");
  const [repo, setRepo] = useState(null);
  const [branch, setBranch] = useState(null);
  const [stages, setStages] = useState([]);


  useEffect(() => {
    const fetchMetaAndConfig = async () => {
      try {
        // Step 1: Get build metadata
        const res = await fetch(`http://35.177.242.182:5000/executions/${buildId}`);
        const data = await res.json();
  
        const repoPath = data.repo_title.replace("/", "_");
        setRepo(repoPath);
        setBranch(data.branch);
  
        // Step 2: Fetch .ci.yml using repo + branch
        const configRes = await fetch(
          `http://35.177.242.182:5000/pipeline-config/${repoPath}?branch=${data.branch}`
        );
        const configData = await configRes.json();
  
        if (configData?.content) {
          setYamlText(configData.content);
  
          // Parse stages ONCE based on initial load
          const parsed = yaml.load(configData.content);
          if (parsed && typeof parsed === "object") {
            const steps = [];
            if (parsed.lint) steps.push("Lint");
            if (parsed.format) steps.push("Format");
            if (parsed.build) steps.push("Build");
            if (parsed.test) steps.push("Test");
            setStages(steps);
          }
        } else {
          setYamlText(
            "WARNING!: .ci.yml file is MISSING / Not found\n   - Tip: Select an existing template from the right or Upload a file"
          );
        }
      } catch (err) {
        console.error("❌ Error loading config:", err);
      }
    };
  
    if (buildId) fetchMetaAndConfig();
  }, [buildId]);

  useEffect(() => {
    try {
      const parsed = yaml.load(yamlText);
      if (parsed && typeof parsed === "object") {
        const steps = [];
        if (parsed.lint) steps.push("Lint");
        if (parsed.format) steps.push("Format");
        if (parsed.build) steps.push("Build");
        if (parsed.test) steps.push("Test");
        setStages(steps);
      } else {
        setStages([]);
      }
    } catch (err) {
      setStages([]);
    }
  }, [yamlText]); // ⬅️ triggers on every editor change

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

  const saveConfig = async () => {
    try {
      const res = await fetch(`http://35.177.242.182:5000/pipeline-config/${repo}`, {
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
        <div className={styles.headerRow}>
          <h1>Pipeline Configuration</h1>
          {repo && branch && (
            <p className={styles.meta}>
              Editing config for: <strong>{repo}</strong> @ <strong>{branch}</strong>
            </p>
          )}
        </div>
      </div>

      <div className={styles.topSection}>
        <YamlEditorCard
          yamlText={yamlText}
          setYamlText={setYamlText}
          onSaveToServer={saveConfig}
        />
        <UploadSelectCard onUpload={handleUpload} onTemplateChange={handleTemplateChange} />
      </div>

      <PipelineVisualiser stages={stages}/>
    </div>
  );
};

export default PipelinePage;