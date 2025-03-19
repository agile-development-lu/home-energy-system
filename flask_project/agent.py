import pandas as pd
from sklearn.cluster import KMeans

class BehavioralSegmentationAgent:
    def __init__(self, data_path=None):
        """
        Initialize the agent with a dataset or an empty DataFrame.
        :param data_path: Path to the dataset file. If None, initializes with an empty DataFrame.
        """
        if data_path:
            self.data = pd.read_csv(data_path)
        else:
            # 初始化空的 DataFrame
            self.data = pd.DataFrame(columns=['appliance', 'usage', 'usage_count'])

        self.appliance_priority = {}

    def update_data(self, new_data):
        """
        Update the internal data with new usage data from the front end.
        :param new_data: List of dictionaries with 'appliance', 'usage', and 'usage_count'.
        """
        self.data = pd.DataFrame(new_data)

    def prioritize_appliances(self):
        """
        Use KMeans clustering to dynamically assign priority to appliances.
        """
        if self.data.empty:
            raise ValueError("No data available to calculate priorities.")

        # Check required columns
        if 'usage' not in self.data.columns or 'usage_count' not in self.data.columns:
            raise ValueError("The dataset must contain 'usage' and 'usage_count' columns.")

        # Perform KMeans clustering
        kmeans = KMeans(n_clusters=3, random_state=42)
        self.data['cluster'] = kmeans.fit_predict(self.data[['usage', 'usage_count']])

        # Map clusters to priorities
        # Cluster with the highest average usage and usage_count -> High Priority
        cluster_means = self.data.groupby('cluster')[['usage', 'usage_count']].mean()
        cluster_means['priority_rank'] = cluster_means.rank(method='dense', ascending=False).mean(axis=1)

        # Map clusters based on their rank
        priority_mapping = cluster_means['priority_rank'].rank(method='dense').astype(int).map({
            1: 'High', 2: 'Medium', 3: 'Low'
        }).to_dict()

        self.data['priority'] = self.data['cluster'].map(priority_mapping)

        # Save the priority result in a dictionary for easier access
        self.appliance_priority = dict(zip(self.data['appliance'], self.data['priority']))

    def get_priorities(self):
        """
        Return the appliance priorities as a dictionary.
        """
        return self.appliance_priority

