import React from "react";
import styles from "./UploadSelectCard.module.css";
import Select from "react-select";

const UploadSelectCard = ({ onUpload, onTemplateChange }) => {
  const options = [
    {value: "python", label: "Python CI"},
    {value: "nodejs", label: "NodeJS Deploy"},
    {value: "default", label: "Default"},

];

  return (
    <div className={styles.card}>
      <h3>Upload YAML File</h3>

      <input 
        type="file" 
        onChange={onUpload} 
        className={styles.upload} 
      />

      <h3>Existing Templates</h3>
      <Select 
        className={styles.select}
        options={options}
        placeholder="Select Template"
      />

    </div>
  );
};

export default UploadSelectCard;