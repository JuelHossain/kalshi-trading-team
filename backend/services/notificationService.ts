import { CONFIG } from '../config';

const DEFAULT_TOPIC = process.env.NTFY_TOPIC || 'kalshi-sentient-alpha';

export const sendNotification = async (
  message: string,
  title: string = 'Kalshi Sentinel',
  priority: 'min' | 'low' | 'default' | 'high' | 'urgent' = 'default'
) => {
  try {
    await fetch(`https://ntfy.sh/${DEFAULT_TOPIC}`, {
      method: 'POST',
      body: message,
      headers: {
        Title: title,
        Priority: priority,
        Tags: 'robot,chart_with_upwards_trend',
      },
    });
    console.log(`[Notification] Sent to ${DEFAULT_TOPIC}: ${title} - ${message}`);
  } catch (e) {
    console.error('[Notification] Delivery Failed:', e);
  }
};
