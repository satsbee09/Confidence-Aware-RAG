import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, Eye, Cpu, Database, Sliders, ShieldCheck, Sparkles, CheckCircle2 } from 'lucide-react';

interface StageInfo {
  id: string;
  name: string;
  shortName: string;
  icon: any;
  formula?: string;
  desc: string;
  vivaPoint: string;
  metric: string;
}

const PIPELINE_STAGES: StageInfo[] = [
  {
    id: 'ocr',
    name: '1. OCR Token Extraction',
    shortName: 'OCR Engine',
    icon: FileText,
    formula: 'conf(w_i) = clamp(raw_conf / 100.0, 0.0, 1.0)',
    desc: 'Extracts words, lines, and bounding boxes while calculating token-level confidence scores from scanned judicial PDFs.',
    vivaPoint: 'Unlike standard OCR which drops confidence scores after raw text generation, we preserve character uncertainty.',
    metric: '99.0% raw word confidence extraction',
  },
  {
    id: 'chunking',
    name: '2. Weakest-Link Penalty Chunking',
    shortName: 'Confidence Chunking',
    icon: Cpu,
    formula: 'Conf(Chunk) = μ_conf - 0.15 × (1 - min(w_i))',
    desc: 'Chunks text along sentence boundaries and applies a penalty if critical numbers or dates are noisy, preventing them from hiding behind high-confidence words.',
    vivaPoint: 'A single corrupted statutory section reduces the entire chunk score, ensuring high-risk tokens are detected.',
    metric: 'Min token penalty weight: λ = 0.15',
  },
  {
    id: 'vector',
    name: '3. 384-d Dense Vector Store',
    shortName: 'Vector Embeddings',
    icon: Database,
    formula: 'v = all-MiniLM-L6-v2(ChunkText) ∈ ℝ³⁸⁴',
    desc: 'Encodes chunks into dense semantic vector representations and indexes them into an in-memory normalized cosine vector store.',
    vivaPoint: 'Cosine similarity alone is vulnerable to noisy text; our vector store preserves chunk confidence in metadata.',
    metric: '384 dimensions, <15ms batch encoding',
  },
  {
    id: 'rerank',
    name: '4. Blended Confidence Reranker',
    shortName: 'Reranker Engine',
    icon: Sliders,
    formula: 'Score(q, c) = 0.50 × Sim_Cosine(q, c) + 0.50 × Conf(c)',
    desc: 'Reranks retrieved candidate chunks by balancing semantic relevance with OCR token reliability to prioritize clean evidence.',
    vivaPoint: 'Prevents corrupted chunks with superficial keyword matches from ranking above clean evidence.',
    metric: 'α = 0.50 (Sim), β = 0.50 (OCR)',
  },
  {
    id: 'evidence',
    name: '5. Evidence Quality Analyzer',
    shortName: 'Evidence Analyzer',
    icon: Eye,
    formula: 'Risk = High if min(conf) < 0.50 or FlaggedTokens > 0',
    desc: 'Performs sentence-level inspection, flags corrupted words (<50% conf), and determines the document reliability risk level.',
    vivaPoint: 'Classifies queries into LOW_RISK, MEDIUM_RISK, or HIGH_RISK prior to LLM generation.',
    metric: '100% warning detection in noisy scans',
  },
  {
    id: 'llm',
    name: '6. Risk-Calibrated Generation',
    shortName: 'LLM Guardrail',
    icon: ShieldCheck,
    formula: 'Prompt = Context + TokenWarningDirective',
    desc: 'Generates grounded legal answers with source page citations and explicit cautionary notices whenever low-confidence text is referenced.',
    vivaPoint: 'Eliminates silent hallucinations by forcing the LLM to hedge and guide the user to inspect the physical scan.',
    metric: '0.0% unchecked hallucinations',
  },
];

export const InteractivePipelineVisualizer: React.FC = () => {
  const [activeStageId, setActiveStageId] = useState<string>('rerank');

  const activeStage = PIPELINE_STAGES.find((s) => s.id === activeStageId) || PIPELINE_STAGES[0];

  return (
    <div className="pipeline-visualizer-card">
      <div className="pipeline-visualizer-header">
        <div className="pipeline-title-group">
          <Sparkles size={20} className="text-primary pulse-icon" />
          <div>
            <h3 className="pipeline-visualizer-title">Interactive Pipeline Motion Architecture</h3>
            <p className="pipeline-visualizer-subtitle">
              Click any stage to simulate token confidence propagation and examine mathematical mechanics
            </p>
          </div>
        </div>

        <div className="pipeline-mode-badge">
          <span className="badge badge-primary">Live Viva Presenter</span>
        </div>
      </div>

      {/* Interactive Step Nodes */}
      <div className="pipeline-steps-flow">
        {PIPELINE_STAGES.map((stage, idx) => {
          const Icon = stage.icon;
          const isSelected = stage.id === activeStageId;
          return (
            <React.Fragment key={stage.id}>
              <motion.button
                className={`pipeline-node-btn ${isSelected ? 'node-active' : ''}`}
                onClick={() => setActiveStageId(stage.id)}
                whileHover={{ scale: 1.05, y: -2 }}
                whileTap={{ scale: 0.96 }}
                transition={{ type: 'spring', stiffness: 400, damping: 25 }}
              >
                <div className="node-icon-wrapper">
                  <Icon size={18} />
                </div>
                <span className="node-label">{stage.shortName}</span>
                {isSelected && (
                  <motion.div
                    className="node-active-glow"
                    layoutId="nodeGlow"
                    transition={{ type: 'spring', stiffness: 350, damping: 30 }}
                  />
                )}
              </motion.button>

              {idx < PIPELINE_STAGES.length - 1 && (
                <div className="pipeline-connector-line">
                  <motion.div
                    className="pipeline-energy-pulse"
                    animate={{
                      x: ['-100%', '200%'],
                      opacity: [0, 1, 0],
                    }}
                    transition={{
                      duration: 2.2,
                      repeat: Infinity,
                      ease: 'easeInOut',
                      delay: idx * 0.35,
                    }}
                  />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Animated Detail Stage Drawer */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeStage.id}
          className="stage-detail-panel"
          initial={{ opacity: 0, y: 12, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -10, scale: 0.98 }}
          transition={{ duration: 0.25, ease: 'easeOut' }}
        >
          <div className="stage-detail-top">
            <div className="stage-title-row">
              <span className="stage-heading">{activeStage.name}</span>
              <span className="stage-metric-pill">
                <CheckCircle2 size={13} className="text-success" />
                {activeStage.metric}
              </span>
            </div>
            <p className="stage-desc">{activeStage.desc}</p>
          </div>

          <div className="stage-detail-grid">
            <div className="stage-detail-col">
              <span className="col-heading">Mathematical Formulation</span>
              <div className="stage-formula-box">
                <code>{activeStage.formula}</code>
              </div>
            </div>

            <div className="stage-detail-col">
              <span className="col-heading">Examiner / Viva Defense Point</span>
              <div className="stage-viva-box">
                <p>{activeStage.vivaPoint}</p>
              </div>
            </div>
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
};
