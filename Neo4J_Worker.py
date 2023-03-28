from neo4j import GraphDatabase
import logging
from neo4j.exceptions import ServiceUnavailable

import os
from datetime import datetime

# Import error raises
from Neo4J_Errors import Uniqueness_Check

# This enables os.getenv() to read the .env file
from dotenv import load_dotenv
load_dotenv()


class App:
    def __init__(self):
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")

        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        # Don't forget to close the driver connection when you are finished with it
        self.driver.close()

    def create_user(self, name, user_id, image_url):
        with self.driver.session(database="neo4j") as session:
            result = session.execute_write(
                self._create_and_return_user, name, user_id, image_url)

            return result

    @staticmethod
    def _create_and_return_user(tx, name, user_id, image_url):
        # MERGE will try to match the entire pattern and if it does not exist, it creates it.
        query = (
            """ MERGE (p:Person { name: $name, user_id: $user_id })
                SET p.image_url = $image_url
                RETURN p.name AS name, p.user_id AS user_id, p.image_url AS image_url
            """
        )
        result = tx.run(query, name=name, user_id=user_id, image_url=image_url)
                        # session_id=session_id, today=today,
                        # joined=joined)

        # Turn the result into a list of dictionaries
        result = result.data()
        
        # Check that only one person with this name and id exists
        Uniqueness_Check(result)        
        
        person = result[0]
        return person

    # def create_user_and_session(self, name, user_id, image_url, session_id):
    #     # Create user and make a relation to the session
    #     with self.driver.session(database="neo4j") as session:
    #         # Write transactions allow the driver to handle retries and transient errors
    #         result = session.execute_write(
    #             self._create_and_return_user_and_session, name, user_id, image_url, session_id)
    #         for row in result:
    #             print("Created user and session between: {p}, {s}".format(
    #                 p=row['p'], s=row['s']))

    def find_person(self, person_name):
        with self.driver.session(database="neo4j") as session:
            result = session.execute_read(
                self._find_and_return_person, person_name)
            for row in result:
                print("Found person: {row}".format(row=row))

    @staticmethod
    def _find_and_return_person(tx, person_name):
        query = (
            "MATCH (p:Person) "
            "WHERE p.name = $person_name "
            "RETURN p.name AS name"
        )
        result = tx.run(query, person_name=person_name)
        return [row["name"] for row in result]
    
    def find_person_by_id(self, user_id):
        with self.driver.session(database="neo4j") as session:
            result = session.execute_read(
                self._find_and_return_person_by_id, user_id)
            print(result)
            
            Uniqueness_Check(result)
            
            return result[0]

    @staticmethod
    def _find_and_return_person_by_id(tx, user_id):
        query = (
            "MATCH (p:Person) "
            "WHERE p.user_id = $user_id "
            "RETURN p.name AS name"
        )
        result = tx.run(query, user_id=user_id)
        return [row["name"] for row in result]

    def get_users(self, session_id):
        with self.driver.session(database="neo4j") as session:
            result = session.execute_read(
                self._get_users, session_id)
            for row in result:
                print("Found person: {row}".format(row=row))

    @staticmethod
    def _get_users(tx, session_id):
        query = (
            """
            MATCH (p:Person)-[:ATTENDED]->(s:Session)
            WHERE s.session_id = $session_id
            RETURN p.name AS name, p.image_url AS image_url
            """
        )
        result = tx.run(query, session_id=session_id)
        return [{"name": row["name"], "image_url": row["image_url"]} for row in result]


if __name__ == "__main__":
    # Aura queries use an encrypted connection using the "neo4j+s" URI scheme
    app = App()
    app.create_user("Asaf Kedem", "123", "https://www.google.com", 0, "18:07")
    app.close()