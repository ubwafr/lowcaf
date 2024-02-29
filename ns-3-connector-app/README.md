# Lowcaf Application for ns-3 

You can use this app in ns-3 to connect to our lowcaf analysis, processing framework. 

## Installation of the ns-3 connector app

1. Install by copying into your ns3-source directory
2. The directory "Lowcaf_ns3_application" must be in the "scratch" directory of your ns-3 source directory

Tested Version is 3.37


## Setting up the ns-3-connector app on a node

```cpp

#include "lapplication.h"

// ...

using namespace ns3;

// ... Set up nodes etc.

int
main(int argc, char* argv[]) {

	Ptr<LApplication> lapplication = CreateObject<LApplication>();
	nodes.Get(0)->AddApplication(lapplication);
	lapplication->SetStartTime(Seconds(1));
	lapplication->SetStopTime(Seconds(10));

// Initialize App as Source Node
// lapplication->InitializeSourceLApp(<SERVER-IP>, <SERVER-PORT>, <NNODE-ID>, <PNODE-ID>, <BIND-TO-NET-DEVICE-INCOMING>);

// Initialize App as Intermediate Node
// lapplication->InitializeIntermediateLApp(<SERVER-IP>, <SERVER-PORT>, <NNODE-ID>, <PNODE-ID>, <BIND-TO-NET-DEVICE-INCOMING>, <BIND-TO-NET-DEVICE-OUTGOING>);

// Initialize App as Sink Node
// lapplication->InitializeSinkLApp(<SERVER-IP>, <SERVER-PORT>, <NNODE-ID>, <PNODE-ID>, <BIND-TO-NET-DEVICE-OUTGOING>);
}



```


## Running your ns-3 app with the Lowcaf ns-3-connector app

1. Open a shell in your ns-3.XX source folder

2. Run the ./ns3 command in your shell building and calling the ns-3-connector app

3. Execute your ns-3 app

~~~bash
NS_LOG="LApplication=debug|info|warn|error|prefix_node|prefix_time:LowcafTwoNodes=info|debug|prefix_time|prefix_node" ./ns3 run "<YOUR-PROGRAM-NAME>"
~~~
