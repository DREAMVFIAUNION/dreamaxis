export const operatorMotion = {
  duration: {
    fast: 0.18,
    base: 0.24,
    slow: 0.34,
  },
  ease: [0.22, 1, 0.36, 1] as const,
};

export const operatorCardMotion = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -6 },
  transition: {
    duration: operatorMotion.duration.base,
    ease: operatorMotion.ease,
  },
};

export const operatorStageMotion = {
  initial: { opacity: 0.72, scale: 0.985 },
  animate: { opacity: 1, scale: 1 },
  transition: {
    duration: operatorMotion.duration.slow,
    ease: operatorMotion.ease,
  },
};

export const operatorStripMotion = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  transition: {
    duration: operatorMotion.duration.fast,
    ease: operatorMotion.ease,
  },
};

export const operatorArtifactMotion = {
  initial: { opacity: 0, scale: 0.98 },
  animate: { opacity: 1, scale: 1 },
  exit: { opacity: 0, scale: 0.98 },
  transition: {
    duration: operatorMotion.duration.base,
    ease: operatorMotion.ease,
  },
};

