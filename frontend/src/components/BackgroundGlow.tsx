import React from 'react';
import { motion } from 'framer-motion';

export const BackgroundGlow: React.FC = () => {
  return (
    <div className="background-glow-container" aria-hidden="true">
      {/* Primary Floating Orb */}
      <motion.div
        className="glow-orb orb-primary"
        animate={{
          x: [0, 40, -30, 0],
          y: [0, -50, 30, 0],
          scale: [1, 1.15, 0.95, 1],
        }}
        transition={{
          duration: 18,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />

      {/* Purple Secondary Orb */}
      <motion.div
        className="glow-orb orb-purple"
        animate={{
          x: [0, -50, 40, 0],
          y: [0, 40, -40, 0],
          scale: [1, 0.9, 1.2, 1],
        }}
        transition={{
          duration: 22,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />

      {/* Cyan Accent Orb */}
      <motion.div
        className="glow-orb orb-cyan"
        animate={{
          x: [0, 30, -40, 0],
          y: [0, 30, -30, 0],
          scale: [0.9, 1.1, 1, 0.9],
        }}
        transition={{
          duration: 25,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />

      {/* Grid Overlay */}
      <div className="glow-grid-overlay" />
    </div>
  );
};
