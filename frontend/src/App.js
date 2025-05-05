import styles from './styles/App.module.css';
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Dashboard from './pages/Dashboard';
import Pipeline from './pages/Pipeline';
import DebugPage from './pages/DebugPage';
import MenuBar from './Components/MenuBar.js';
import NavigateToLastOrFirstBuild from './Components/DebugCards/NavigateToLastBuild.js';

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
          <Route path="/pipeline-config" element={<Pipeline />} />
          <Route path="/debug/:buildId" element={<DebugPage />} />
          <Route path="/debug" element={<NavigateToLastOrFirstBuild />} />
        </Routes>
      </div>
    </Router>
  );
  
}


export default App;
