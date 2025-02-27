import logo from './logo.svg';
import styles from './styles/App.module.css';
import SemiCircularProgressBar from './Components/SemiCircularProgressBar';

console.log('Imported styles:', styles);

function App() {
  return (
    <div className={styles.App}>
      <header className={styles.Appheader}>
        <img src={logo} className={styles.Applogo} alt="logo" />
        <p>
          Edit <code>src/App.js</code> and save to reload.
        </p>
        <a
          className={styles.Applink}
          href="https://reactjs.org"
          target="_blank"
          rel="noopener noreferrer"
        >
          Learn React today
        </a>
      </header>
      <div className={styles.section}>
        <div className={styles.container}>
          <div className={styles.progressBarContainer}>
            <h1>unit-tests</h1>
            <SemiCircularProgressBar value={5} gauge="Low" />
          </div>
        </div>
        <div className={styles.container}>
          <div className={styles.progressBarContainer}>
            <SemiCircularProgressBar value={7} gauge="Moderate" />
          </div>
        </div>
        <div className={styles.container}>
          <div className={styles.progressBarContainer}>
            <SemiCircularProgressBar value={9} gauge="High" />
          </div>
        </div>
        <div className={styles.container}>
          <div className={styles.progressBarContainer}>
            <SemiCircularProgressBar value={11} gauge="Very High" />
          </div>
        </div>
      </div>

    </div>
  );
  
}


export default App;
