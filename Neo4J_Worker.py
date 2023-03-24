from neo4j import GraphDatabase
import logging
from neo4j.exceptions import ServiceUnavailable

import os
from datetime import datetime

# This enables os.getenv() to read the .env file
from dotenv import load_dotenv
load_dotenv()

class App:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        # Don't forget to close the driver connection when you are finished with it
        self.driver.close()

    def create_user(self, name, user_id, image_url, session_id, session_start):
        # Create user and make a relation to the session
        with self.driver.session(database="neo4j") as session:
            # Write transactions allow the driver to handle retries and transient errors
            result = session.execute_write(
                self._create_and_return_user, name, user_id, image_url, session_id, session_start)
            for row in result:
                print("Created user between: {p}, {s}".format(p=row['p'], s=row['s']))

    @staticmethod
    def _create_and_return_user(tx, name, user_id, image_url, session_id, session_start):
        # To learn more about the Cypher syntax, see https://neo4j.com/docs/cypher-manual/current/
        # The Reference Card is also a good resource for keywords https://neo4j.com/docs/cypher-refcard/current/
        
        # TODO: get this from the frontend, when the session_id is generated. 
        # Joined should be the time the user joined the session
        # Time should be the time the session was created
        
        # Get the current date and time
        today = datetime.today()
        today = today.strftime("%Y-%m-%d")

        joined = datetime.now()
        joined = joined.strftime("%H:%M")


        # Send the query to the database
        # MERGE will try to match the entire pattern and if it does not exist, it creates it.
        query = (
            """CREATE (p:Person { name: $name, user_id: $user_id, image_url: $image_url })
            MERGE (s:Session { session_id: $session_id, date: $today, time_started: $session_start })
            CREATE (p)-[:ATTENDED {joined: $joined}]->(s) 
            RETURN p, s"""
        )
        result = tx.run(query, name=name, user_id=user_id, image_url=image_url,
                           session_id=session_id, today=today, session_start=session_start, 
                           joined=joined)
        try:
            return [{"p": row["p"]["name"], "s": row["s"]["session_id"]}
                    for row in result]
        # Capture any errors along with the query and data for traceability
        except ServiceUnavailable as exception:
            logging.error("{query} raised an error: \n {exception}".format(
                query=query, exception=exception))
            raise

    # def create_friendship(self, person1_name, person2_name):
    #     with self.driver.session(database="neo4j") as session:
    #         # Write transactions allow the driver to handle retries and transient errors
    #         result = session.execute_write(
    #             self._create_and_return_friendship, person1_name, person2_name)
    #         for row in result:
    #             print("Created friendship between: {p1}, {p2}".format(p1=row['p1'], p2=row['p2']))

    # @staticmethod
    # def _create_and_return_friendship(tx, person1_name, person2_name):
    #     # To learn more about the Cypher syntax, see https://neo4j.com/docs/cypher-manual/current/
    #     # The Reference Card is also a good resource for keywords https://neo4j.com/docs/cypher-refcard/current/
    #     query = (
    #         "CREATE (p1:Person { name: $person1_name }) "
    #         "CREATE (p2:Person { name: $person2_name }) "
    #         "CREATE (p1)-[:KNOWS]->(p2) "
    #         "RETURN p1, p2"
    #     )
    #     result = tx.run(query, person1_name=person1_name, person2_name=person2_name)
    #     try:
    #         return [{"p1": row["p1"]["name"], "p2": row["p2"]["name"]}
    #                 for row in result]
    #     # Capture any errors along with the query and data for traceability
    #     except ServiceUnavailable as exception:
    #         logging.error("{query} raised an error: \n {exception}".format(
    #             query=query, exception=exception))
    #         raise

    def __find_latest_session(self):
        with self.driver.session(database="neo4j") as session:
            result = session.execute_read(self._find_latest_session)
            print("Found session: {result}".format(result=result))
        return result

    @staticmethod
    def _find_latest_session(tx):
        query = (
            """MATCH (s:Session)
            WITH  max(s.session_id) AS maximum
            RETURN maximum"""
        )
        result = tx.run(query)
        return [row["maximum"] for row in result][0]
    
    def find_person(self, person_name):
        with self.driver.session(database="neo4j") as session:
            result = session.execute_read(self._find_and_return_person, person_name)
            for row in result:
                print("Found person: {row}".format(row=row))

    @staticmethod
    def _find_and_return_person(tx, person_name):
        query = (
            "MATCH (p:Consultant) "
            "WHERE p.name = $person_name "
            "RETURN p.name AS name"
        )
        result = tx.run(query, person_name=person_name)
        return [row["name"] for row in result]


if __name__ == "__main__":
    # Aura queries use an encrypted connection using the "neo4j+s" URI scheme
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    app = App(uri, user, password)
    app.create_user("Asaf Kedem", "123", "https://www.google.com", 0, "18:07")
    app.close()