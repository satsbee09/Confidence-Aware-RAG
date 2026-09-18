import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, 
  ShieldCheck, 
  Eye, 
  Sparkles, 
  Layers, 
  Sliders, 
  CheckCircle,
  ArrowRight,
  BookOpen
} from 'lucide-react';

interface HelpGuideModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const HelpGuideModal: React.FC<HelpGuideModalProps> = ({ isOpen, onClose }) => {
  const [activeStep, setActiveStep] = useState<number>(1);

  const steps = [
    {
      step: 1,
      title: 'What is Confidence-Aware RAG?',
      subtitle: 'The Problem of Silent AI Hallucinations in Legal Documents',
      icon: ShieldCheck,
      content: (
        <div className="help-step-content">
          <p>
            Standard AI / RAG systems blindly trust all extracted text from scanned PDFs. 
            When judicial orders, affidavits, or RTI records suffer from <strong>smudges, faded ink, or low-resolution photocopying</strong>, standard OCR produces silent corruptions (e.g., misreading <em>"Rs. 25,000"</em> as <em>"Rs. 25"</em>).
          </p>
          <div className="help-callout-box">
            <Sparkles size={20} className="text-primary flex-shrink-0" />
            <div>
              <strong>Our Innovation:</strong> We track and propagate word-level OCR confidence scores ($0.0 - 1.0$) from the scanner all the way to the AI answer, preventing false assertions.
            </div>
          </div>
        </div>
      ),
    },
    {
      step: 2,
      title: 'How to Use the 3-Column Dashboard',
      subtitle: 'Documents List • Live PDF Viewer • AI Answer Panel',
      icon: Layers,
      content: (
        <div className="help-step-content">
          <div className="help-grid-3">
            <div className="help-col-card">
              <span className="step-num-pill">1</span>
              <h4>Select Document</h4>
              <p>Choose any scanned legal order or RTI reply from the left panel. View its average OCR quality score.</p>
            </div>
            <div className="help-col-card">
              <span className="step-num-pill">2</span>
              <h4>Live Document Canvas</h4>
              <p>See the physical scanned page. The exact text used by the AI is highlighted with bounding boxes.</p>
            </div>
            <div className="help-col-card">
              <span className="step-num-pill">3</span>
              <h4>AI Answer & Citations</h4>
              <p>Read the grounded answer, check the OCR confidence score, and click <em>"View in Document"</em> to jump to any page.</p>
            </div>
          </div>
        </div>
      ),
    },
    {
      step: 3,
      title: 'Understanding Bounding Box Colors',
      subtitle: 'Interpreting Word-Level Confidence Overlays',
      icon: Eye,
      content: (
        <div className="help-step-content">
          <p>
            Every word on the physical document is tracked with its coordinate bounding box $[x_0, y_0, x_1, y_1]$:
          </p>
          <div className="help-color-legend">
            <div className="color-legend-card color-green">
              <span className="color-indicator green" />
              <div>
                <strong>High Confidence (≥ 85%)</strong>
                <p>Crisp, highly readable text. Highly reliable evidence.</p>
              </div>
            </div>
            <div className="color-legend-card color-amber">
              <span className="color-indicator amber" />
              <div>
                <strong>Moderate Confidence (70% – 84%)</strong>
                <p>Minor noise or slight font distortion. Review recommended for key figures.</p>
              </div>
            </div>
            <div className="color-legend-card color-red">
              <span className="color-indicator red" />
              <div>
                <strong>Low Confidence / Risk (&lt; 70%)</strong>
                <p>Degraded, noisy, or corrupted OCR tokens. AI surfaces an explicit warning banner.</p>
              </div>
            </div>
          </div>
        </div>
      ),
    },
    {
      step: 4,
      title: 'Evaluating System Robustness',
      subtitle: 'Side-by-Side Comparison & Optical Noise Playground',
      icon: Sliders,
      content: (
        <div className="help-step-content">
          <p>
            Test how the system behaves under stress:
          </p>
          <ul className="help-features-list">
            <li>
              <strong>Compare (Baseline) Tab:</strong> See side-by-side how Normal RAG hallucinates false claims on noisy scans while Confidence-Aware RAG detects the degradation and alerts the user.
            </li>
            <li>
              <strong>Evaluation & Benchmarks:</strong> Drag the optical noise slider (0% to 40%) to simulate real-world physical photocopying, contrast fading, and skew.
            </li>
          </ul>
        </div>
      ),
    },
  ];

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="modal-backdrop" onClick={onClose}>
        <motion.div
          className="help-guide-modal-card"
          onClick={(e) => e.stopPropagation()}
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ duration: 0.25 }}
        >
          {/* Header */}
          <div className="help-modal-header">
            <div className="help-header-title">
              <BookOpen size={20} className="text-primary" />
              <h3>DocSage User Guide & Architecture Tour</h3>
            </div>
            <button className="modal-close-btn" onClick={onClose}>
              <X size={18} />
            </button>
          </div>

          {/* Stepper Navigation */}
          <div className="help-stepper-bar">
            {steps.map((s) => {
              const StepIcon = s.icon;
              return (
                <button
                  key={s.step}
                  className={`help-step-nav-btn ${activeStep === s.step ? 'active' : ''}`}
                  onClick={() => setActiveStep(s.step)}
                >
                  <StepIcon size={14} />
                  <span>Step {s.step}: {s.title}</span>
                </button>
              );
            })}
          </div>

          {/* Step Body */}
          <div className="help-modal-body">
            <div className="help-step-header">
              <h3>{steps[activeStep - 1].title}</h3>
              <p className="help-step-subtitle">{steps[activeStep - 1].subtitle}</p>
            </div>
            {steps[activeStep - 1].content}
          </div>

          {/* Footer Navigation */}
          <div className="help-modal-footer">
            <button
              className="help-nav-btn"
              disabled={activeStep <= 1}
              onClick={() => setActiveStep((prev) => prev - 1)}
            >
              Previous
            </button>

            <span className="help-step-indicator">
              Step {activeStep} of {steps.length}
            </span>

            {activeStep < steps.length ? (
              <button
                className="help-nav-btn primary"
                onClick={() => setActiveStep((prev) => prev + 1)}
              >
                <span>Next</span>
                <ArrowRight size={14} />
              </button>
            ) : (
              <button className="help-nav-btn primary" onClick={onClose}>
                <CheckCircle size={14} />
                <span>Got it, Start Exploring!</span>
              </button>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
