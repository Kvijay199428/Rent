import { useState } from "react";
import { faqItems } from "../data";
import { useScrollReveal } from "@shared/motion";

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const { ref: headerRef, motionStyle: headerStyle } = useScrollReveal();

  return (
    <section className="faq-section" id="faq">
      <div className="section-container">
        <div className="section-header" ref={headerRef} style={headerStyle}>
          <span className="section-badge">05 — FAQ</span>
          <h2 className="section-title">Frequently asked questions</h2>
          <div className="section-rule" />
          <p className="section-subtitle">
            Quick answers to common questions about the platform.
          </p>
        </div>
        <div className="faq-list">
          {faqItems.map((item, i) => (
            <div key={i} className={`faq-item ${openIndex === i ? "open" : ""}`}>
              <button
                className="faq-question"
                onClick={() => setOpenIndex(openIndex === i ? null : i)}
                aria-expanded={openIndex === i}
              >
                <span>{item.question}</span>
                <span className="faq-chevron" aria-hidden="true">{openIndex === i ? "−" : "+"}</span>
              </button>
              <div className="faq-answer">
                <div className="faq-answer-inner">
                  <p>{item.answer}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}