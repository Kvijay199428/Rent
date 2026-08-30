import { useState } from "react";
import { faqItems } from "../data";

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section className="faq-section" id="faq">
      <div className="section-container">
        <div className="section-header">
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
              {openIndex === i && (
                <div className="faq-answer">
                  <p>{item.answer}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
