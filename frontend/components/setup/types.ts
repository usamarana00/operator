export type GithubRepo = {
  full_name: string;
  owner: string;
  repo_name: string;
  html_url: string;
  private: boolean;
  description: string;
  updated_at: string;
};

export type Milestone = {
  title: string;
  due_date: string;
};

export type ProjectConfig = {
  repo: GithubRepo;
  name: string;
  client: string;
  milestones: Milestone[];
};
