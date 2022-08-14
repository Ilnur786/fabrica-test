from sqlalchemy.orm import scoped_session
from datetime import datetime
import requests as req
import time
from loguru import logger
from pathlib import Path
import os
# CURRENT PROJECT IMPORTS
from db_api import SessionLocal
from db_api import Distribution, Client, Message


def main():
    logger.add('./logs/run.log', format="{time: %Y-%m-%d %H:%M:%S} - {level} - {message}", level="INFO")
    TOKEN = os.getenv('JWT_TOKEN')
    db_session = scoped_session(SessionLocal)
    send_status_cases = ['SENT', 'NOT_SENT', 'FAIL']
    s = req.session()
    s.headers.update({"ContentType": "application/json", "Authorization": TOKEN})
    while True:
        distrs = db_session.query(Distribution).filter(Distribution.end_date >= datetime.now()).all()
        if distrs:
            for distr in distrs:
                clients = db_session.query(Client).filter_by(tag=distr.client_filter).all()
                for client in clients:
                    msg = db_session.query(Message).filter_by(distribution_id=distr.id, client_id=client.id).first()
                    if msg is None:
                        msg = Message(distribution_id=distr.id, client_id=client.id)
                        db_session.add(msg)
                        db_session.flush()
                    elif msg.send_status == 'SENT':
                        continue
                    payload = {
                        "id": msg.id,
                        "phone": client.mobile_number,
                        "text": distr.text
                    }
                    r = s.post(url=f'https://probe.fbrq.cloud/v1/send/{msg.id}', json=payload)
                    if r.status_code == 200:
                        msg.send_status = "SENT"
                        msg.send_date = datetime.now()
                        logger.info(f'MESSAGE - {msg} was SENT to CLIENT - {client} within DISTRIBUTION {distr}')
                        logger.info(f'CLIENT - {client} receive MESSAGE - {msg}')
                        logger.info(f"DISTRIBUTION'S - {distr} MESSAGE - {msg} was SENT")
                    else:
                        msg.send_status = "FAIL"
                        logger.info(f'MESSAGE - {msg} SENDING IS FAILED')
                    db_session.commit()
        print('Up to date', datetime.now().strftime('%Y-%m-%d %H:%M'), flush=True)
        time.sleep(30)


if __name__ == '__main__':
    main()
