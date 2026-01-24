import { kalshiService } from '../../services/kalshiService';

export const executeEmergencyProtocol = async (isPaperTrading: boolean) => {
  // Agent 12: Ragnarok (The Nuclear Option)
  console.warn('!!! [Agent 12] RAGNAROK PROTOCOL INITIATED !!!');

  try {
    // 1. Fetch All Resting Orders
    const ordersResponse = await kalshiService.fetch(
      '/portfolio/orders',
      'GET',
      undefined,
      isPaperTrading
    );
    const openOrders = ordersResponse?.orders || [];
    console.log(`[Agent 12] Detected ${openOrders.length} open orders. Terminating...`);

    // 2. Iterate + Cancel (Atomic Deletion)
    const cancellationPromises = openOrders.map((order: any) => {
      console.log(`[Agent 12] Nuking Order: ${order.order_id} (${order.ticker})`);
      return kalshiService.fetch(
        `/portfolio/orders/${order.order_id}`,
        'DELETE',
        undefined,
        isPaperTrading
      );
    });

    const results = await Promise.allSettled(cancellationPromises);
    const failedCount = results.filter(
      (r: PromiseSettledResult<any>) =>
        r.status === 'rejected' || (r.status === 'fulfilled' && !r.value)
    ).length;

    if (failedCount > 0) {
      console.warn(`[Agent 12] Partial Deletion: ${failedCount} orders failed to cancel.`);
    } else {
      console.log('[Agent 12] RAGNAROK SUCCESS: Airspace payload cleared.');
    }

    // 3. (Optional) Liquidate Positions
    // V2 manual liquidation is high-risk. For now, stop at order cancellation.

    return {
      status: failedCount === 0 ? 'CONTAINED' : 'PARTIAL_SUCCESS',
      action: `Cancelled ${openOrders.length - failedCount}/${openOrders.length} orders`,
    };
  } catch (e) {
    console.error(
      '[Agent 12] RAGNAROK FAILURE: Core meltdown. Immediate manual intervention needed.',
      e
    );
    throw e;
  }
};
