import { type ReactNode, Component } from "react";

import { type SingleCoCoSettingsResponse, normalizeSingleCoCoSettingsResponse } from "components/coco-attestation/api";
import CoCoSettingsForm from "components/coco-attestation/CoCoSettingsForm";
import { Settings } from "components/coco-attestation/Utils";
import { Messages, MessageType, Utils as MessagesUtils } from "components/messages/messages";
import { TopPanel } from "components/panels/TopPanel";
import { Loading } from "components/utils";

import Network, { type JsonResult } from "utils/network";

type Props = {
  serverId: number;
  availableEnvironmentTypes: object;
  showOnScheduleOption?: boolean;
};

type State = {
  messages: MessageType[];
  supported: boolean;
  settings: Settings;
  loading: boolean;
};

class CoCoSettings extends Component<Props, State> {
  public static readonly defaultProps: Partial<Props> = {
    showOnScheduleOption: true,
  };

  constructor(props: Props) {
    super(props);

    this.state = {
      messages: [],
      supported: false,
      loading: true,
      settings: {
        enabled: false,
        environmentType: Object.values(this.props.availableEnvironmentTypes)[0],
        attestOnBoot: false,
        attestOnSchedule: false,
      },
    };

    this.init();
  }

  init(): void {
    this.setState({ loading: true });

    Network.get(`/rhn/manager/api/systems/${this.props.serverId}/details/coco/settings`).then(
      this.handleResult,
      this.handleRequestError
    );
  }

  render(): ReactNode {
    if (this.state.loading) {
      return (
        <div className="panel panel-default">
          <Loading />
        </div>
      );
    }

    return (
      <TopPanel title={t("Settings")} icon="fa fa-pencil-square-o">
        <Messages items={this.state.messages} />
        {this.state.supported && (
          <CoCoSettingsForm
            initialData={this.state.settings}
            saveHandler={this.onSave}
            availableEnvironmentTypes={this.props.availableEnvironmentTypes}
            showOnScheduleOption={this.props.showOnScheduleOption}
          />
        )}
      </TopPanel>
    );
  }

  onSave = (data: Settings) => {
    Network.post(`/rhn/manager/api/systems/${this.props.serverId}/details/coco/settings`, data).then(
      this.handleResult,
      this.handleRequestError
    );
  };

  handleResult = (result: JsonResult<SingleCoCoSettingsResponse>) => {
    if (!result.success) {
      this.setState({
        messages: MessagesUtils.error(result.messages),
        loading: false,
      });
      return;
    }

    const response = normalizeSingleCoCoSettingsResponse(result.data);
    if (!response.supported) {
      this.setState({
        supported: false,
        messages: MessagesUtils.warning(result.messages),
        loading: false,
      });
    } else {
      this.setState({
        messages: MessagesUtils.success(result.messages),
        supported: true,
        settings: response.settings,
        loading: false,
      });
    }
  };

  handleRequestError = (err) => {
    this.setState({
      messages: Network.responseErrorMessage(err),
      supported: false,
      loading: false,
      settings: {
        enabled: false,
        environmentType: Object.values(this.props.availableEnvironmentTypes)[0],
        attestOnBoot: false,
        attestOnSchedule: false,
      },
    });
  };
}

export default CoCoSettings;
