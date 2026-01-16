import React from 'react';

interface ThinkingBubbleProps {
  text: string;
}

const ThinkingBubble: React.FC<ThinkingBubbleProps> = ({ text }) => {
  return (
    <div className="font-mono text-sm text-gray-300">
      <span className="text-emerald-500 mr-2">{'>'}</span>
      <span className="typewriter">{text}</span>
    </div>
  );
};

export default ThinkingBubble;
