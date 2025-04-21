import React from "react";
import { Link, useLocation } from "react-router-dom";
import styles from "../styles/App.module.css";

const MenuBar = () => {
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  return (
    <nav className={styles.sidebar}>
      <Link to="/dashboard" className={isActive("/dashboard") ? styles.active : ""}> Dashboard </Link>
      <Link to="/pipeline" className={isActive("/pipeline") ? styles.active : ""}> Pipeline </Link>
      <Link to="/debug" className={isActive("/debug") ? styles.active : ""}> Debug </Link>
    </nav>
  );
};

export default MenuBar;