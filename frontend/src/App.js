// import logo from './logo.svg';
import styles from './styles/App.module.css';
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Dashboard from './pages/Dashboard';
// not yet ready
// import Pipeline from './pages/Pipeline';
import DebugPage from './pages/DebugPage';
import MenuBar from './Components/MenuBar.js';

console.log('Imported styles:', styles);

function App() {
  return (
    <Router>
      <div className={styles.App}>
        <div className={styles.MenuBar}>
          <MenuBar />
        </div>

        <Routes>
          <Route path="/dashboard" element={<Dashboard Repo_name={"REPO NAME"}/>} /> {/*UPDATE THE REPO NAME HERE*/}
          {/* <Route path="/pipeline" element={<Pipeline />} /> */}
          <Route path="/debug" element={<DebugPage />} />
        </Routes>
      </div>
    </Router>
  );
  
}


export default App;
