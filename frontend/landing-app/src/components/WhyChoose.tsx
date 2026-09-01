import { useState } from "react";
import { whyChooseFeatures, screenshotTabs } from "../data";
import { Logo } from "@shared/brand/Logo";

export default function WhyChoose() {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <section className="why-section" id="benefits">
      <div className="why-grid">
        <div className="why-content">
          <span className="section-badge">Why Rent</span>
          <h2 className="section-title">Built for modern landlords</h2>
          <div className="section-rule" />
          <p className="section-subtitle">
            Stop chasing payments and chasing paperwork. The platform automates
            the tedious parts of rent management so you can focus on what
            matters.
          </p>
          <ul className="benefits-list">
            {whyChooseFeatures.map((item) => (
              <li key={item}>
                <span className="check-icon">✓</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div className="why-preview">
          <div className="screenshot-tabs">
            {screenshotTabs.map((tab, i) => (
              <button
                key={tab}
                className={`screenshot-tab ${i === activeTab ? "active" : ""}`}
                onClick={() => setActiveTab(i)}
              >
                {tab}
              </button>
            ))}
          </div>
          <div className="screenshot-placeholder">
            <div className="mockup-header">
              <div className="mockup-dots">
                <span className="mockup-dot red" />
                <span className="mockup-dot yellow" />
                <span className="mockup-dot green" />
              </div>
              <span className="mockup-title"><Logo height={13} /> — {screenshotTabs[activeTab]}</span>
            </div>
            <div className="mockup-body">
              <div className="mockup-label">{screenshotTabs[activeTab]} — Live</div>
              <div className="mockup-bars">
                <div className="mockup-bar" style={{ width: "80%" }} />
                <div className="mockup-bar" style={{ width: "60%" }} />
                <div className="mockup-bar" style={{ width: "90%" }} />
                <div className="mockup-bar" style={{ width: "45%" }} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
