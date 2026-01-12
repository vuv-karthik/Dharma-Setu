'use client';

import { motion } from 'framer-motion';

export function TypingIndicator() {
    return (
        <div className="flex gap-4 justify-start">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0 shadow-sm mt-1">
                <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                    className="w-4 h-4 border-2 border-white border-t-transparent rounded-full"
                />
            </div>
            <div className="bg-white border border-slate-100 px-5 py-4 rounded-2xl rounded-tl-sm shadow-sm flex items-center gap-1.5">
                {[0, 1, 2].map((dot) => (
                    <motion.div
                        key={dot}
                        className="w-2 h-2 bg-blue-500 rounded-full"
                        animate={{
                            y: [0, -6, 0],
                            opacity: [0.6, 1, 0.6]
                        }}
                        transition={{
                            duration: 0.8,
                            repeat: Infinity,
                            delay: dot * 0.2,
                            ease: "easeInOut"
                        }}
                    />
                ))}
                <span className="text-xs text-slate-400 font-medium ml-2">Analyzing...</span>
            </div>
        </div>
    );
}
