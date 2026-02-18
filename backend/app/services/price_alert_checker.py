"""
Price alert checker.

Compares active alerts against recent price snapshots
and triggers alerts when price drops below threshold.
"""

import logging

from app.db import get_db, get_pending_alerts, trigger_alert

logger = logging.getLogger(__name__)


async def check_price_alerts() -> list[dict]:
    """
    Check all pending price alerts against recent price snapshots.
    Returns list of triggered alerts with details.
    """
    alerts = await get_pending_alerts()
    if not alerts:
        return []

    db = await get_db()
    triggered: list[dict] = []

    for alert in alerts:
        target_price = alert["target_price"]
        normalized_query = alert.get("normalized_query", "")
        part_number = alert.get("part_number")
        brand = alert.get("brand")

        # Build query for recent price snapshots
        conditions = ["created_at > datetime('now', '-7 days')"]
        params: list = []

        if part_number:
            conditions.append("UPPER(part_number) = ?")
            params.append(part_number.upper())
        elif normalized_query:
            conditions.append("query = ?")
            params.append(normalized_query)

        if brand:
            conditions.append("brand = ?")
            params.append(brand)

        where = " AND ".join(conditions)
        cursor = await db.execute(
            f"""SELECT price, source, url
                FROM price_snapshots
                WHERE {where}
                ORDER BY price ASC
                LIMIT 1""",
            params,
        )
        row = await cursor.fetchone()

        if row:
            lowest_price = row[0]
            source = row[1]
            url = row[2]

            if lowest_price <= target_price:
                success = await trigger_alert(
                    alert["id"],
                    current_lowest=lowest_price,
                    source=source,
                    url=url,
                )
                if success:
                    triggered.append(
                        {
                            "alert_id": alert["id"],
                            "query": alert.get("query", ""),
                            "part_number": part_number,
                            "target_price": target_price,
                            "current_lowest": lowest_price,
                            "source": source,
                            "url": url,
                        }
                    )
                    logger.info(
                        f"Price alert triggered: {part_number or normalized_query} "
                        f"at ${lowest_price:.2f} (target: ${target_price:.2f})"
                    )

    return triggered
