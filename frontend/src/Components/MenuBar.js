import React from "react";
import { Link, useLocation } from "react-router-dom";
import styles from "../styles/App.module.css";

const MenuBar = () => {
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  const menuItems = [
    { name: "Debug", icon: "log.png", path: "/debug" },
    { name: "Pipeline", icon: "pipeline.png", path: "/pipeline" },
    { name: "Dashboard", icon: "dashboard.png", path: "/dashboard" },
    { name: "Account", icon:"user_1.png", path: "/user-details"}
  ];

  return (
    <nav className={styles.menuBar}>
      {menuItems.map((item) => (
        <Link
          key={item.name}
          to={item.path}
          className={`${styles.menuItem} ${isActive(item.path) ? styles.active : ""}`}
        >
          <img
            src={`${process.env.PUBLIC_URL}/icons/${item.icon}`}
            alt={`${item.name} icon`}
            className={styles.icon}
          />
        </Link>
      ))}
    </nav>
  );
};

export default MenuBar;