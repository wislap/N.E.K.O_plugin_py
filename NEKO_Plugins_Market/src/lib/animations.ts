import type { Variants } from 'framer-motion';

export const pageTransition: Variants = {
  initial: {
    opacity: 0,
    y: 14,
    filter: 'blur(6px)'
  },
  animate: {
    opacity: 1,
    y: 0,
    filter: 'blur(0px)',
    transition: {
      duration: 0.28,
      ease: [0.22, 1, 0.36, 1]
    }
  },
  exit: {
    opacity: 0,
    y: -10,
    filter: 'blur(4px)',
    transition: {
      duration: 0.18,
      ease: [0.4, 0, 1, 1]
    }
  }
};

export const listContainer: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.045,
      delayChildren: 0.04
    }
  }
};

export const listItem: Variants = {
  initial: {
    opacity: 0,
    y: 18,
    scale: 0.985
  },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: 0.32,
      ease: [0.22, 1, 0.36, 1]
    }
  }
};

export const softReveal: Variants = {
  initial: {
    opacity: 0,
    y: 10
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.24,
      ease: [0.22, 1, 0.36, 1]
    }
  },
  exit: {
    opacity: 0,
    y: -6,
    transition: {
      duration: 0.16
    }
  }
};
