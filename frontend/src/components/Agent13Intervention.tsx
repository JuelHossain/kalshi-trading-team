import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

export class Agent13Intervention extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error, errorInfo: null };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        this.setState({ errorInfo });
        console.error("Agent 13 Intercepted Error:", error, errorInfo);
    }

    handleRestart = () => {
        window.location.reload();
    };

    render() {
        if (this.state.hasError) {
            return (
                <div className="fixed inset-0 z-50 bg-[#050505] flex items-center justify-center font-mono text-center p-8">
                    <div className="max-w-2xl w-full relative">
                        {/* Red Tech Border */}
                        <div className="absolute inset-0 border border-red-500/30 rounded-3xl animate-pulse"></div>
                        <div className="absolute -inset-1 border border-red-500/10 rounded-3xl blur-md"></div>

                        <div className="relative z-10 p-12 bg-black/80 backdrop-blur-xl rounded-3xl overflow-hidden">
                            {/* Header */}
                            <div className="mb-8">
                                <div className="text-6xl mb-4">👾</div>
                                <h1 className="text-3xl font-bold text-red-500 uppercase tracking-[0.2em] mb-2 font-tech">
                                    SYSTEM MALFUNCTION
                                </h1>
                                <div className="text-xs text-red-400/50 uppercase tracking-widest">
                                    CRITICAL UI FAILURE DETECTED
                                </div>
                            </div>

                            {/* Agent 13 Message */}
                            <div className="bg-red-900/10 border border-red-500/20 p-6 rounded-xl mb-8 text-left relative">
                                <div className="absolute -top-3 left-4 bg-black px-2 text-[10px] text-red-500 font-bold uppercase tracking-widest border border-red-500/20">
                                    AGENT 13 :: FIXER
                                </div>
                                <p className="text-red-200 text-sm leading-relaxed typing-effect">
                                    "Anomaly detected in the render cycle. I've intercepted the crash dump.
                                    The visual interface has destabilized. Proceeding with emergency containment."
                                </p>
                                <div className="mt-4 pt-4 border-t border-red-500/10 text-[10px] text-red-400/60 font-mono break-all bg-black/30 p-2 rounded">
                                    Error: {this.state.error && this.state.error.toString()}
                                </div>
                            </div>

                            {/* Actions */}
                            <button
                                onClick={this.handleRestart}
                                className="group relative px-8 py-3 bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/50 rounded-lg transition-all active:scale-95 uppercase tracking-widest text-xs font-bold overflow-hidden"
                            >
                                <span className="relative z-10 group-hover:text-red-100 transition-colors">Reboot Neural Trace</span>
                                <div className="absolute inset-0 bg-red-500/0 group-hover:bg-red-500/10 transition-colors duration-300"></div>
                            </button>

                            <div className="mt-8 text-[9px] text-gray-700 uppercase tracking-[0.3em]">
                                SENTIENT_OS // PROTECTED MODE
                            </div>
                        </div>
                    </div>

                    {/* Background Noise Effect */}
                    <div className="absolute inset-0 pointer-events-none opacity-[0.03] bg-[url('https://grainy-gradients.vercel.app/noise.svg')]"></div>
                </div>
            );
        }

        return this.props.children;
    }
}
