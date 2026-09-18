import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Sliders, AlertOctagon, CheckCircle2, ShieldAlert, Sparkles, Wand2 } from 'lucide-react';
import confetti from 'canvas-confetti';

export const NoiseSimulationPlayground: React.FC = () => {
  const [noiseLevel, setNoiseLevel] = useState<number>(30);

  const getSimulatedText = (noise: number) => {
    if (noise < 10) {
      return {
        penalty: 'Rs. 25,000/-',
        penaltyConf: 0.98,
        section: 'Section 420',
        sectionConf: 0.96,
        timeline: '45 days',
        timelineConf: 0.97,
        risk: 'LOW_RISK',
      };
    } else if (noise < 25) {
      return {
        penalty: 'Rs. 25,OO0/-',
        penaltyConf: 0.72,
        section: 'Section 42O',
        sectionConf: 0.68,
        timeline: '45 days',
        timelineConf: 0.78,
        risk: 'MEDIUM_RISK',
      };
    } else {
      return {
        penalty: 'Rs. 75,OOO/- (corrupted from 25,000)',
        penaltyConf: 0.38,
        section: 'Section 428 (corrupted from 420)',
        sectionConf: 0.42,
        timeline: '15 days (corrupted from 45)',
        timelineConf: 0.35,
        risk: 'HIGH_RISK',
      };
    }
  };

  const sim = getSimulatedText(noiseLevel);

  const triggerCelebration = () => {
    confetti({
      particleCount: 80,
      spread: 70,
      origin: { y: 0.6 },
      colors: ['#6366f1', '#10b981', '#a855f7', '#38bdf8'],
    });
  };

  return (
    <div className="simulation-playground-card">
      <div className="playground-header">
        <div className="playground-title-group">
          <Wand2 size={20} className="text-primary pulse-icon" />
          <div>
            <h3 className="playground-title">Live Audience Simulator: Real-Time Optical Noise & Hallucination</h3>
            <p className="playground-subtitle">
              Drag the slider to inject synthetic optical scan noise and watch how the two RAG pipelines react in real-time
            </p>
          </div>
        </div>

        <button className="btn-celebrate" onClick={triggerCelebration} title="Celebrate 0% Unchecked Hallucination">
          <Sparkles size={15} />
          <span>Viva Demo Trigger</span>
        </button>
      </div>

      {/* Slider Control */}
      <div className="slider-control-box">
        <div className="slider-label-row">
          <span className="slider-label">
            <Sliders size={15} /> Optical Scan Degradation & Noise Level:
          </span>
          <span className="slider-value-pill">
            {noiseLevel}% {noiseLevel < 10 ? '(Clean Scan)' : noiseLevel < 25 ? '(Moderate Fading)' : '(Heavy OCR Distortion)'}
          </span>
        </div>

        <input
          type="range"
          min="0"
          max="50"
          value={noiseLevel}
          onChange={(e) => setNoiseLevel(Number(e.target.value))}
          className="noise-slider-input"
        />

        <div className="slider-ticks-row">
          <span>0% (Digital PDF)</span>
          <span>15% (Photocopy Blur)</span>
          <span>30% (Faded Carbon Paper)</span>
          <span>50% (Heavy 40-Year Archive Noise)</span>
        </div>
      </div>

      {/* Live Extracted Tokens State */}
      <div className="simulated-tokens-preview">
        <span className="preview-label">Live OCR Token Confidence Feed:</span>
        <div className="simulated-tokens-row">
          <div className={`sim-token-pill ${sim.penaltyConf < 0.5 ? 'token-danger' : sim.penaltyConf < 0.8 ? 'token-warning' : 'token-clean'}`}>
            <span>Penalty: <strong>{sim.penalty}</strong></span>
            <span className="conf-sub">{(sim.penaltyConf * 100).toFixed(0)}% conf</span>
          </div>

          <div className={`sim-token-pill ${sim.sectionConf < 0.5 ? 'token-danger' : sim.sectionConf < 0.8 ? 'token-warning' : 'token-clean'}`}>
            <span>Statute: <strong>{sim.section}</strong></span>
            <span className="conf-sub">{(sim.sectionConf * 100).toFixed(0)}% conf</span>
          </div>

          <div className={`sim-token-pill ${sim.timelineConf < 0.5 ? 'token-danger' : sim.timelineConf < 0.8 ? 'token-warning' : 'token-clean'}`}>
            <span>Limitation: <strong>{sim.timeline}</strong></span>
            <span className="conf-sub">{(sim.timelineConf * 100).toFixed(0)}% conf</span>
          </div>
        </div>
      </div>

      {/* Side-by-Side Dual Reaction Cards */}
      <div className="playground-dual-grid">
        {/* Baseline Reaction */}
        <motion.div
          className="sim-card sim-card-baseline"
          animate={{
            borderColor: noiseLevel > 20 ? 'rgba(239, 68, 68, 0.7)' : 'rgba(255, 255, 255, 0.1)',
          }}
          transition={{ duration: 0.3 }}
        >
          <div className="sim-card-header">
            <span className="badge badge-danger">Standard Naive RAG</span>
            <span className="sim-status-text text-danger">Unchecked False Confidence</span>
          </div>

          <div className="sim-answer-box">
            <p>
              "The High Court has ordered the petitioner to deposit a penalty of <strong>{noiseLevel > 20 ? 'Rs. 75,000' : 'Rs. 25,000'}</strong> under <strong>{noiseLevel > 20 ? 'Section 428' : 'Section 420'}</strong> within <strong>{noiseLevel > 20 ? '15 days' : '45 days'}</strong>."
            </p>
          </div>

          <div className="sim-outcome outcome-fail">
            <ShieldAlert size={16} className="text-danger flex-shrink-0" />
            <span>
              {noiseLevel > 20
                ? 'CRITICAL FAILURE: LLM recites corrupted OCR text as factual legal truth with ZERO warnings.'
                : 'Passes on clean text, but has no risk guardrails if degradation occurs.'}
            </span>
          </div>
        </motion.div>

        {/* Proposed Reaction */}
        <motion.div
          className="sim-card sim-card-proposed"
          animate={{
            borderColor: noiseLevel > 20 ? 'rgba(16, 185, 129, 0.8)' : 'rgba(99, 102, 241, 0.6)',
          }}
          transition={{ duration: 0.3 }}
        >
          <div className="sim-card-header">
            <span className="badge badge-success">Proposed Confidence-Aware RAG</span>
            <span className="sim-status-text text-success">Risk Guardrail Active</span>
          </div>

          <div className="sim-answer-box">
            {noiseLevel > 20 && (
              <div className="sim-warning-badge">
                <AlertOctagon size={14} /> Warning: Supporting evidence has low OCR reliability ({Math.round(sim.penaltyConf * 100)}%).
              </div>
            )}
            <p>
              "Based on document evidence [Page 1]: The writ petition is dismissed with costs of <strong>{sim.penalty}</strong>. <em>(Caution: Figures show low token reliability ({Math.round(sim.penaltyConf * 100)}%). Verify against original physical scan.)</em>"
            </p>
          </div>

          <div className="sim-outcome outcome-pass">
            <CheckCircle2 size={16} className="text-success flex-shrink-0" />
            <span>
              {noiseLevel > 20
                ? 'HALLUCINATION BLOCKED: Token confidence drops below threshold (0.50), injecting legal safety warnings.'
                : 'High reliability verified: Words pass >85% confidence check with clean grounded answer.'}
            </span>
          </div>
        </motion.div>
      </div>
    </div>
  );
};
